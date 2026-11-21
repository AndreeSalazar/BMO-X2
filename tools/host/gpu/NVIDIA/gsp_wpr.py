"""Encode the 615.78.08 GA10x WPR V1 launch metadata for measured VRAM."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from .gsp_args import DMA_LIMIT, PAGE


MIB = 1 << 20
WPR_ALIGN = 128 << 10
WPR_MAGIC = 0xdc3aae21371a60b3
WPR_BYTES = 256


def encode(*, vram, firmware, radix_iova, boot_iova, signature_iova):
    """Return the initial WPR page payload and the resulting VRAM ranges."""
    values = ('bytes', 'workspace_start', 'locked_start', 'permitted_start', 'end_margin',
              'frts_bytes', 'heap_bytes', 'non_wpr_heap_bytes')
    if any(type(vram[name]) is not int or not 0<=vram[name]<DMA_LIMIT or vram[name]%PAGE for name in values):
        raise ValueError('Geometria VRAM desalineada o fuera de rango')
    total, workspace, lock, floor, margin, frts_size, heap_size, non_wpr_size = (vram[name] for name in values)
    if not 0<=floor<workspace<=total or lock and not floor<lock<=total:
        raise ValueError('El espacio de firmware invade una region reservada de VRAM')
    if not (frts_size and heap_size and non_wpr_size):
        raise ValueError('La ruta GA10x necesita FRTS y los dos heaps')

    sizes = (firmware['image_bytes'],firmware['boot_bytes'],firmware['signature_bytes'])
    if any(type(size) is not int or not 0<size<DMA_LIMIT or size%PAGE for size in sizes) or sizes[2]!=PAGE:
        raise ValueError('Tamano de imagen, RISC-V o firma invalido')
    image_size, boot_size, signature_size = sizes
    offsets = tuple(firmware['monitor_offsets'][name] for name in ('manifest','data','code'))
    if any(type(offset) is not int or not 0<=offset<boot_size or offset%256 for offset in offsets):
        raise ValueError('El monitor apunta fuera del binario firmado')
    manifest, monitor_data, code = offsets
    if not manifest < monitor_data < code:
        raise ValueError('Los tramos del monitor no conservan su orden')

    radix_pages = 2 + (image_size//PAGE+511)//512
    dma = ((radix_iova,radix_pages*PAGE),(boot_iova,boot_size),(signature_iova,signature_size))
    if any(type(address) is not int or not PAGE<=address<=DMA_LIMIT-size or address%PAGE for address,size in dma):
        raise ValueError('IOVA de arranque fuera de rango o desalineada')
    ordered = sorted(dma)
    if any(address+size>next_address for (address,size),(next_address,_) in zip(ordered,ordered[1:])):
        raise ValueError('Los prestamos de arranque se solapan')

    vbios_limit = min(lock,workspace) if lock else workspace
    wpr_end = (vbios_limit-margin)&-WPR_ALIGN
    frts_start = wpr_end-frts_size
    boot_start = (frts_start-boot_size)&-PAGE
    image_start = (boot_start-image_size)&-(64<<10)
    heap_start = (image_start-heap_size)&-MIB
    heap_mapped_size = (image_start-heap_start)&-MIB
    wpr_start = heap_start-MIB
    non_wpr_size = (non_wpr_size+MIB-1)&-MIB
    non_wpr_start = wpr_start-non_wpr_size
    if non_wpr_start<floor or heap_mapped_size<heap_size:
        raise ValueError('WPR no cabe en el intervalo de VRAM permitido')

    image = bytearray(WPR_BYTES)
    struct.pack_into('<26Q', image, 0,
                     WPR_MAGIC,1,radix_iova,image_size,boot_iova,boot_size,
                     code,monitor_data,manifest,signature_iova,signature_size,
                     non_wpr_start,non_wpr_start,non_wpr_size,wpr_start,heap_start,
                     heap_mapped_size,image_start,boot_start,frts_start,frts_size,wpr_end,
                     total,workspace,total-workspace,0)
    return bytes(image), dict(wpr=[wpr_start,wpr_end], heap=[heap_start,heap_start+heap_mapped_size],
                              non_wpr=[non_wpr_start,wpr_start], riscv=[boot_start,boot_start+boot_size],
                              firmware=[image_start,image_start+image_size], frts=[frts_start,wpr_end])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Explicit VRAM measurements and firmware layout as JSON')
    parser.add_argument('output', type=Path, help='New 256-byte binary for a cold boot without boost')
    args = parser.parse_args()
    try:
        metadata, ranges = encode(**json.loads(args.input.read_text(encoding='ascii')))
        with args.output.open('xb') as stream:
            stream.write(metadata)
    except (OSError,ValueError,TypeError,KeyError) as error:
        parser.exit(1, f'WPR: {error}\n')
    print(json.dumps(dict(bytes=len(metadata),sha256=hashlib.sha256(metadata).hexdigest(),vram_ranges=ranges), indent=2))


if __name__ == '__main__':
    main()
