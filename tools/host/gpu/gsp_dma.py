"""Prepare the 615.78.08 firmware pages and their AMD-Vi boot mappings."""

import hashlib
import json
import struct

from firmware import PROFILES, layout, verify
from radix3 import ENTRIES, PAGE, encode


RELEASE = '615.78.08'
READ = 1 << 61
WRITE = 1 << 62
READ_WRITE = READ | WRITE
DEVICE_TABLE_PAGES = 96
DOMAIN = 5
RID_GRAPHICS = 0x2900
RID_AUDIO = 0x2901
MODE2 = 2 << 9
TABLE_LIMIT = 1 << 30


def load_firmware(directory):
    profiles = json.loads(PROFILES.read_text(encoding='ascii'))
    info = verify(directory, RELEASE, profiles['releases'][RELEASE])['gsp']
    path = directory / info['name']
    with path.open('rb') as source:
        image = source.read(info['bytes'] + 1)
    if len(image) != info['bytes'] or hashlib.sha256(image).hexdigest() != info['sha256']:
        raise ValueError('GSP original cambio durante la lectura')
    return image


def aligned_payload(container, first_iova):
    """Return aligned firmware, signature and Radix3 pages in DMA order."""
    info = layout(container, RELEASE)
    image, signature = (info['sections'][name] for name in ('.fwimage', '.fwsignature_ga10x'))
    image_bytes = image['bytes']
    if image_bytes % PAGE or signature['bytes'] != PAGE:
        raise ValueError('La imagen y firma GA10x requieren paginas completas')
    image_pages = image_bytes // PAGE
    leaves = (image_pages + ENTRIES - 1) // ENTRIES
    middle = (leaves + ENTRIES - 1) // ENTRIES
    addresses = [first_iova + index*PAGE for index in range(image_pages)]
    signature_iova = first_iova + image_bytes
    root_iova = signature_iova + PAGE
    directory_addresses = [root_iova + index*PAGE for index in range(1+middle+leaves)]
    _, directory = encode(addresses, directory_addresses)
    aligned = b''.join((container[image['offset']:image['offset']+image_bytes],
                        container[signature['offset']:signature['offset']+PAGE], directory))
    return aligned, dict(firmware_bytes=image_bytes, signature_iova=signature_iova,
                         radix3_iova=root_iova, read_only_pages=len(aligned)//PAGE)


def build_tables(device_table, roots, backing, first_iova, payload_pages):
    """Emit deny-by-default DTEs, read-only firmware and one writable reply page."""
    addresses = (device_table, roots, backing, first_iova)
    if any(type(addr) is not int or addr < PAGE or addr % PAGE for addr in addresses):
        raise ValueError('Bases DMA desalineadas o invalidas')
    if type(payload_pages) is not int or not 0 < payload_pages < TABLE_LIMIT//PAGE:
        raise ValueError('Cantidad de paginas DMA fuera de rango')
    reply_iova = first_iova + (payload_pages+1)*PAGE
    if reply_iova+PAGE > TABLE_LIMIT:
        raise ValueError('El rango no cabe en una tabla AMD-Vi de dos niveles')
    first_leaf = first_iova >> 21
    leaf_count = (reply_iova >> 21) - first_leaf + 1
    device_bytes = DEVICE_TABLE_PAGES * PAGE
    tree_bytes = (2+leaf_count) * PAGE
    ranges = sorted(((device_table, device_bytes), (roots, tree_bytes),
                     (backing, (payload_pages+1)*PAGE)))
    if (any(base+size > (1 << 52) for base,size in ranges) or
            any(base+size > following for (base,size),(following,_) in zip(ranges,ranges[1:]))):
        raise ValueError('Las reservas fisicas se solapan o exceden 52 bits')

    # The first root is empty and denies DMA from unassigned requesters.
    # An all-zero DTE can imply passthrough on the QEMU model.
    denied = struct.pack('<4Q', roots | MODE2 | READ_WRITE | 3, 0, 0, 0)
    devices = bytearray(denied * (device_bytes//32))
    root = roots + PAGE
    struct.pack_into('<4Q', devices, RID_GRAPHICS*32, root | MODE2 | READ_WRITE | 3, DOMAIN, 0, 0)

    tree = bytearray(tree_bytes)
    for leaf in range(leaf_count):
        address = roots + (2+leaf)*PAGE
        struct.pack_into('<Q', tree, PAGE+(first_leaf+leaf)*8, address | (1 << 9) | READ_WRITE | 1)
    for page in range(payload_pages+1):
        destination = page == payload_pages
        iova = reply_iova if destination else first_iova+page*PAGE
        leaf = (iova >> 21) - first_leaf
        slot = (iova >> 12) & (ENTRIES-1)
        permission = READ_WRITE if destination else READ
        phys = backing+page*PAGE
        struct.pack_into('<Q', tree, (2+leaf)*PAGE+slot*8, phys | permission | 1)
    return bytes(devices), bytes(tree), reply_iova, denied
