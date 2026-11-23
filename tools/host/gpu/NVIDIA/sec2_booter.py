"""Prepare a DMA-aligned copy of the signed GA10x SEC2 load booter in HOST."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from .firmware import BIN_HEADER, read_native_files, read_verified


HS_HEADER = struct.Struct('<9I')
LOAD_HEADER = struct.Struct('<9I')  # Header and one application descriptor.
SIGNATURE_BYTES = 384  # RSA-3072.
PAGE_BYTES = 4096
SEC2_UCODE1_FUSE = 0x824140


def sec2_booter_layout(container):
    """Return V2 SEC2 load ranges. The caller authenticates the container."""
    if len(container) < BIN_HEADER.size:
        raise ValueError('SEC2 booter: cabecera truncada')
    magic, version, length, hs_offset, image_offset, image_bytes = BIN_HEADER.unpack_from(container)
    if ((magic, version, length) != (0x10de, 1, (len(container) + 255) & -256)
            or not BIN_HEADER.size <= hs_offset <= image_offset - HS_HEADER.size
            or image_offset + image_bytes != len(container)
            or not image_bytes or image_bytes % 256):
        raise ValueError('SEC2 booter: contenedor invalido')

    (signature_offset, signature_bytes, patch_location_offset, patch_signature_offset,
     metadata_offset, metadata_bytes, count_offset, load_offset,
     load_bytes) = HS_HEADER.unpack_from(container, hs_offset)
    if metadata_bytes != 12 or load_bytes != LOAD_HEADER.size:
        raise ValueError('SEC2 booter: tamano de metadatos desconocido')
    metadata_ranges = (
        (signature_offset, signature_bytes),
        (patch_location_offset, 4),
        (patch_signature_offset, 4),
        (metadata_offset, metadata_bytes),
        (count_offset, 4),
        (load_offset, load_bytes),
    )
    end = hs_offset + HS_HEADER.size
    for offset, size in sorted(metadata_ranges):
        if offset < end or offset % 4 or not 0 < size <= image_offset - offset:
            raise ValueError('SEC2 booter: metadatos fuera de rango o solapados')
        end = offset + size

    slot, = struct.unpack_from('<I', container, patch_location_offset)
    first_signature, = struct.unpack_from('<I', container, patch_signature_offset)
    count, = struct.unpack_from('<I', container, count_offset)
    fuse_versions, engine_mask, ucode_id = struct.unpack_from('<3I', container, metadata_offset)
    if (not fuse_versions or (engine_mask, ucode_id) != (1, 3)
            or not count or first_signature % SIGNATURE_BYTES
            or first_signature + count * SIGNATURE_BYTES != signature_bytes):
        raise ValueError('SEC2 booter: firmas o destino SEC2 invalidos')

    (os_code, os_bytes, dmem, dmem_bytes, apps, imem, imem_bytes,
     _, app_data_bytes) = LOAD_HEADER.unpack_from(container, load_offset)
    if (apps != 1 or app_data_bytes or os_code != 0 or not os_bytes or os_bytes % 256
            or imem < os_bytes or imem % 256 or not imem_bytes or imem_bytes % 256
            or dmem < imem + imem_bytes or dmem % 256 or not dmem_bytes or dmem_bytes % 256
            or dmem + dmem_bytes != image_bytes or not dmem <= slot <= image_bytes - SIGNATURE_BYTES):
        raise ValueError('SEC2 booter: segmentos o destino de firma invalidos')

    return {
        'image_offset': image_offset,
        'imem': {'offset': imem, 'bytes': imem_bytes},
        'dmem': {'offset': dmem, 'bytes': dmem_bytes},
        'bootvec': imem,
        'signature': {
            'source': signature_offset + first_signature,
            'dmem_offset': slot - dmem,
            'bytes': SIGNATURE_BYTES,
            'count': count,
            'fuse_versions': fuse_versions,
        },
        'engine_mask': engine_mask,
        'ucode_id': ucode_id,
    }


def prepare_sec2_booter(container, fuse_word):
    """Materialize an authenticated container using a caller-supplied SEC2 fuse read."""
    if (type(fuse_word) is not int or not 0 <= fuse_word < 0xffffffff
            or fuse_word >> 20 == 0xbad):
        raise ValueError('SEC2 booter: lectura del fusible invalida')
    layout = sec2_booter_layout(container)
    signature = layout['signature']
    version = (fuse_word & 0xffff).bit_length()
    # The SEC2 HS booter uses a scalar version, unlike the FWSEC version mask.
    index = signature['count'] - 1 if version == 0 else signature['fuse_versions'] - version
    if not 0 <= index < signature['count']:
        raise ValueError('SEC2 booter: no hay firma para la version del fusible')
    source = signature['source'] + index * signature['bytes']
    slot = layout['dmem']['offset'] + signature['dmem_offset']
    image = bytearray(container[layout['image_offset']:])
    image[slot:slot + signature['bytes']] = container[source:source + signature['bytes']]
    image.extend(bytes(-len(image) % PAGE_BYTES))
    return bytes(image), {
        'scope': 'HOST',
        'fuse_register': SEC2_UCODE1_FUSE + 4 * (layout['ucode_id'] - 1),
        'fuse_word': fuse_word,
        'fuse_version': version,
        'signature_index': index,
        'imem': layout['imem'],
        'dmem': layout['dmem'],
        'dmem_signature_offset': signature['dmem_offset'],
        'bootvec': layout['bootvec'],
        'engine_mask': layout['engine_mask'],
        'ucode_id': layout['ucode_id'],
        'dma_pages': len(image) // PAGE_BYTES,
        'sha256': hashlib.sha256(image).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Verified NVIDIA release directory')
    parser.add_argument('--fuse-word', type=lambda word: int(word, 0), required=True,
                        help='Raw SEC2 signature fuse word, from a live measurement or HOST test')
    parser.add_argument('--output', type=Path, help='New file for the signed, page-aligned image')
    args = parser.parse_args()
    try:
        files = read_native_files(args.directory)
        container = read_verified(args.directory, files['booter_load'])
        image, receipt = prepare_sec2_booter(container, args.fuse_word)
        if args.output:
            with args.output.open('xb') as stream:
                stream.write(image)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
