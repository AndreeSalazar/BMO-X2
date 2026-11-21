"""Write the optional NVIDIA boot payload and its matching reader parameters."""

import hashlib
import json
import zlib

from .firmware import NATIVE_RELEASE, layout, read_native_files, read_verified, riscv_bootloader


def boot_chain(directory, files):
    monitor, offsets = riscv_bootloader(read_verified(directory, files['bootloader']))
    chain = bytearray()
    entries = {}
    payloads = {'riscv': monitor}
    for role in ('booter_load', 'booter_unload'):
        payloads[role] = read_verified(directory, files[role])
    for role, payload in payloads.items():
        entries[role] = dict(offset=len(chain), bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        chain.extend(payload)
        chain.extend(bytes(-len(chain) % 4096))
    return bytes(chain), dict(entries=entries, monitor_offsets=offsets, pages=len(chain)//4096,
                              sha256=hashlib.sha256(chain).hexdigest())


def stage_firmware(run, directory, prepare):
    files = read_native_files(directory)
    firmware = read_verified(directory, files['gsp'])
    sections = layout(firmware,NATIVE_RELEASE)
    archive = firmware
    layout_boot = None
    flags = ['-DBMO_NVIDIA_GSP_STAGE']
    if prepare:
        image = sections['sections']['.fwimage']
        signature = sections['sections']['.fwsignature_ga10x']
        if (not image['bytes'] or image['bytes']%4096 or signature['bytes']!=4096
                or signature['offset']<image['offset']+image['bytes']):
            raise ValueError('The NVIDIA preparation requires ordered whole-page slices')
        flags += ['-DBMO_NVIDIA_GSP_PREPARE','-DBMO_NVIDIA_GSP_QUEUES','-DBMO_NVIDIA_GSP_LIBOS',
                  f'-DBMO_GSP_IMAGE_OFFSET={image["offset"]}',
                  f'-DBMO_GSP_IMAGE_BYTES={image["bytes"]}',
                  f'-DBMO_GSP_SIGNATURE_OFFSET={signature["offset"]}']
        chain, layout_boot = boot_chain(directory, files)
        flags += ['-DBMO_NVIDIA_GSP_BOOT_CHAIN',f'-DBMO_GSP_BOOT_FILE_OFFSET={len(firmware)}',
                  f'-DBMO_GSP_BOOT_PAGES={layout_boot["pages"]}']
        archive += chain
    crc = zlib.crc32(archive)
    flags += [f'-DBMO_GSP_FILE_BYTES={len(archive)}', f'-DBMO_GSP_FILE_CRC={crc}']
    (run/'GSP.BIN').write_bytes(archive)
    corrupted = bytearray(archive)
    corrupted[-1 if layout_boot else len(archive)//2] ^= 1
    (run/'corrupted-gsp.bin').write_bytes(corrupted)
    metadata = dict(release=NATIVE_RELEASE,bytes=len(archive),sha256=hashlib.sha256(archive).hexdigest(),
                    crc32=crc,layout=sections,prepare=prepare,detached_dma=prepare,queues=prepare,libos=prepare)
    if layout_boot:
        metadata.update(firmware_file_sha256=files['gsp']['sha256'],boot_chain=layout_boot)
    (run/'nvidia-gsp-stage.json').write_text(json.dumps(metadata)+'\n',encoding='ascii')
    return archive,flags
