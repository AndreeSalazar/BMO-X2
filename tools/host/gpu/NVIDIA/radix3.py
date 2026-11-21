"""Encode a GSP firmware Radix3 directory from assigned DMA addresses."""

import argparse
import hashlib
import json
from pathlib import Path
import struct


PAGE = 4096
ENTRIES = PAGE // 8
DMA_LIMIT = 1 << 52


def encode(firmware_iovas, directory_iovas):
    """Return root IOVA and pages ordered root, middle, leaves."""
    image_pages = len(firmware_iovas)
    if not 1 <= image_pages <= ENTRIES**3:
        raise ValueError('Radix3: cantidad de paginas de imagen fuera de rango')
    leaves = (image_pages + ENTRIES - 1) // ENTRIES
    middle = (leaves + ENTRIES - 1) // ENTRIES
    if len(directory_iovas) != 1 + middle + leaves:
        raise ValueError('Radix3: cantidad de paginas del directorio incorrecta')
    seen = set()
    for addresses in (directory_iovas, firmware_iovas):
        for address in addresses:
            if type(address) is not int or not PAGE <= address < DMA_LIMIT or address % PAGE:
                raise ValueError('Radix3: IOVA fuera de rango o desalineada')
            if address in seen:
                raise ValueError('Radix3: IOVA duplicada en imagen o directorio')
            seen.add(address)

    directory = bytearray(len(directory_iovas)*PAGE)
    # GSP directory entries contain device-visible addresses as raw LE64.
    # A level occupies a whole number of pages and unused entries stay zero.
    levels = ((0,directory_iovas[1:1+middle]),
              (PAGE,directory_iovas[1+middle:]),
              ((1+middle)*PAGE,firmware_iovas))
    for offset,children in levels:
        for index,iova in enumerate(children):
            struct.pack_into('<Q',directory,offset+index*8,iova)
    return directory_iovas[0],bytes(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iovas', type=Path, help='JSON with firmware_iovas and directory_iovas arrays')
    parser.add_argument('output', type=Path, help='New binary directory file')
    args = parser.parse_args()
    try:
        spec = json.loads(args.iovas.read_text(encoding='ascii'))
        if (not isinstance(spec,dict) or set(spec)!={'firmware_iovas','directory_iovas'} or
                any(not isinstance(value,list) for value in spec.values())):
            raise ValueError('Radix3: se requieren dos listas de IOVA')
        root,directory = encode(**spec)
        with args.output.open('xb') as stream:
            stream.write(directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP: {error}\n')
    print(json.dumps(dict(root_iova=root, bytes=len(directory),
                          directory_pages=len(directory)//PAGE,
                          sha256=hashlib.sha256(directory).hexdigest()),indent=2))


if __name__=='__main__':
    main()
