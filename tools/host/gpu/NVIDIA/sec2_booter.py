"""Describe the signed GA10x SEC2 booter without modifying its bytes."""

import struct

from .firmware import BIN_HEADER


HS_HEADER = struct.Struct('<9I')
LOAD_HEADER = struct.Struct('<9I')  # Header and one application descriptor.
SIGNATURE_BYTES = 384  # RSA-3072.


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
