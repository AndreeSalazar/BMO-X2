"""Encode the 615.78.08 GA10x WPR V1 launch metadata for measured VRAM."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from .gsp_args import DMA_LIMIT, PAGE


MIB = 1 << 20
WPR_ALIGN = 128 << 10
WPR_MAGIC = 0xdc3aae21371a60b3
WPR_BYTES = 256
VBIOS_RELOCATED_WORKSPACE_BYTES = 128 << 10


def decode_bootlog(log):
    """Decode the live limits without treating missing or denied reads as zero."""
    lines = log.splitlines()
    if not lines or lines[0]!='BMO-X2 DESKTOP UEFI PRE-EBS':
        raise ValueError('Se requiere GPULOG.TXT de BMO-X2 antes de ExitBootServices')
    names = ('GPU_NVIDIA_ID','GPU_NVIDIA_CMD','GPU_MMIO_STATUS','WPR')
    fields = {}
    for line in lines:
        name, _, value = line.partition('=')
        if name in names:
            if name in fields:
                raise ValueError(f'Campo repetido en el registro: {name}')
            fields[name] = value
    if fields.get('GPU_NVIDIA_ID')!='250410DE' or fields.get('GPU_MMIO_STATUS')!='00000008':
        raise ValueError('Falta la comprobacion PCI de GA106')
    command = fields.get('GPU_NVIDIA_CMD','')
    if not re.fullmatch(r'[\da-fA-F]{8}',command,flags=re.ASCII) or int(command,16)&6!=2:
        raise ValueError('PCI Command no confirma MMIO habilitado con DMA inactivo')
    raw = fields.get('WPR','').split(',')
    if len(raw)!=8 or any(not re.fullmatch(r'[\da-fA-F]{8}',word,flags=re.ASCII) for word in raw):
        raise ValueError('Falta la muestra WPR completa')
    words = [int(word,16) for word in raw]
    if any(word==0xffffffff or word>>20==0xbad for word in words):
        raise ValueError('La GPU devolvio una lectura PRI no valida')
    gfw_access, gfw, usable_mib, vga, lock_access, lock_lo, lock_hi, wpr_hi = words
    if not gfw_access&1 or not lock_access&1:
        raise ValueError('El firmware restringe la lectura de GFW o del bloqueo MMU')
    if gfw&0xff!=0xff or not 1<usable_mib<DMA_LIMIT//MIB:
        raise ValueError('GFW aun no confirmo el arranque y la VRAM util')
    vram = usable_mib*MIB
    raw_workspace = (vga>>8)<<16 if vga&8 else None
    if raw_workspace is not None and raw_workspace>=vram:
        raise ValueError('El espacio VGA queda fuera de la VRAM util')
    workspace = vram-MIB if raw_workspace is None else raw_workspace
    if raw_workspace is not None and workspace<vram-MIB:
        workspace = vram-VBIOS_RELOCATED_WORKSPACE_BYTES
    lock_start, lock_end = ((value>>4)*PAGE for value in (lock_lo,lock_hi))
    lock = [lock_start,lock_end] if lock_start<=lock_end else None
    if lock and lock_end>=vram:
        raise ValueError('La region bloqueada por VBIOS queda fuera de la VRAM util')
    return dict(vram_bytes=vram, vga_workspace_raw=raw_workspace,
                workspace_start=workspace, mmu_locked_pages=lock,
                wpr2_active=bool(wpr_hi>>4), gfw_ready=True)


def encode(*, vram, firmware, radix_iova, boot_iova, signature_iova):
    """Return the initial WPR page payload and the resulting VRAM ranges."""
    values = ('bytes', 'workspace_start', 'permitted_start', 'end_margin',
              'frts_bytes', 'heap_bytes', 'non_wpr_heap_bytes')
    lock = vram['locked_start']
    sizes = [vram[name] for name in values]
    addresses = sizes if lock is None else [*sizes, lock]
    if any(type(value) is not int or not 0<=value<DMA_LIMIT or value%PAGE for value in addresses):
        raise ValueError('Geometria VRAM desalineada o fuera de rango')
    total, workspace, floor, margin, frts_size, heap_size, non_wpr_size = sizes
    if not 0<=floor<workspace<=total or (lock is not None and not floor<lock<=total):
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

    vbios_limit = workspace if lock is None else min(lock,workspace)
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
    parser.add_argument('output', nargs='?', type=Path, help='New 256-byte binary for a cold boot without boost')
    parser.add_argument('--from-bootlog', action='store_true', help='Print the GPU limits in a pre-EBS GPULOG.TXT')
    args = parser.parse_args()
    if args.from_bootlog == (args.output is not None):
        parser.error('Especifica una salida WPR binaria o --from-bootlog')
    try:
        payload = args.input.read_text(encoding='ascii')
        if args.from_bootlog:
            print(json.dumps(decode_bootlog(payload),indent=2))
            return
        metadata, ranges = encode(**json.loads(payload))
        with args.output.open('xb') as stream:
            stream.write(metadata)
    except (OSError,ValueError,TypeError,KeyError) as error:
        parser.exit(1, f'WPR: {error}\n')
    print(json.dumps(dict(bytes=len(metadata),sha256=hashlib.sha256(metadata).hexdigest(),vram_ranges=ranges), indent=2))


if __name__ == '__main__':
    main()
