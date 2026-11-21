"""Write the optional NVIDIA boot payload and its matching reader parameters."""

import json
import zlib

from .firmware import NATIVE_RELEASE, layout, read_native_gsp


def stage_firmware(run, directory, prepare):
    firmware, info = read_native_gsp(directory)
    sections = layout(firmware,NATIVE_RELEASE)
    crc = zlib.crc32(firmware)
    flags = ['-DBMO_NVIDIA_GSP_STAGE',f'-DBMO_GSP_FILE_BYTES={len(firmware)}',
             f'-DBMO_GSP_FILE_CRC={crc}']
    if prepare:
        image = sections['sections']['.fwimage']
        signature = sections['sections']['.fwsignature_ga10x']
        if (not image['bytes'] or image['bytes']%4096 or signature['bytes']!=4096
                or signature['offset']<image['offset']+image['bytes']):
            raise ValueError('The NVIDIA preparation requires ordered whole-page slices')
        flags += ['-DBMO_NVIDIA_GSP_PREPARE','-DBMO_NVIDIA_GSP_QUEUES',
                  f'-DBMO_GSP_IMAGE_OFFSET={image["offset"]}',
                  f'-DBMO_GSP_IMAGE_BYTES={image["bytes"]}',
                  f'-DBMO_GSP_SIGNATURE_OFFSET={signature["offset"]}']
    (run/'GSP.BIN').write_bytes(firmware)
    corrupted = bytearray(firmware)
    corrupted[len(firmware)//2] ^= 1
    (run/'corrupted-gsp.bin').write_bytes(corrupted)
    metadata = dict(release=NATIVE_RELEASE,bytes=len(firmware),sha256=info['sha256'],
                    crc32=crc,layout=sections,prepare=prepare,detached_dma=prepare,queues=prepare)
    (run/'nvidia-gsp-stage.json').write_text(json.dumps(metadata)+'\n',encoding='ascii')
    return firmware,flags
