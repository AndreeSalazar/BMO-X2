"""Build and verify the constrained FAT16 specimen used by the QEMU GZIP test."""

import struct
import zlib


SECTOR = 512
OUTPUT_NAME = b'OUTPUT  GZ '
FAT_HEADS = (1 * SECTOR, 33 * SECTOR)
JOURNAL_COPIES = (78 * SECTOR, 79 * SECTOR)


def initial_image():
    image = bytearray(8192 * SECTOR)
    image[:11] = b'\xeb\x3c\x90BMO-X2  '
    struct.pack_into('<HBHBHHBHHHII', image, 11, SECTOR, 1, 1, 2, 32, 8192, 0xf8, 32, 32, 8, 0, 0)
    struct.pack_into('<BBBI11s8s', image, 36, 0x80, 0, 0x29, 0x324f4d42, b'BMO GZIP   ', b'FAT16   ')
    image[510:512] = b'\x55\xaa'
    for fat in FAT_HEADS:
        struct.pack_into('<6H', image, fat, 0xfff8, 0xffff, 0, 0xffff, 0, 0xffff)
        struct.pack_into('<H', image, fat + 26, 0xfff7)
        struct.pack_into('<H', image, fat + 28, 0xfff7)
    for slot, name, cluster, content in (
        (0, b'KEEP    TXT', 3, b'BMO FAT16 control\r\n'),
        (1, b'KEEP2   TXT', 5, b'BMO FAT16 fragmentation control\r\n'),
    ):
        entry = 65 * SECTOR + slot * 32
        image[entry:entry + 11] = name
        image[entry + 11] = 0x20
        struct.pack_into('<HHHI', image, entry + 22, 0, 0x5d7b, cluster, len(content))
        start = (67 + cluster - 2) * SECTOR
        image[start:start + len(content)] = content
    return bytes(image)


def output_layout(image):
    sector_size, sectors_per_cluster, reserved, copies, entries = struct.unpack_from('<HBHBH', image, 11)
    sectors_per_fat, = struct.unpack_from('<H', image, 22)
    root = (reserved + copies * sectors_per_fat) * sector_size
    data = root + ((entries * 32 + sector_size - 1) // sector_size) * sector_size
    for entry in range(root, root + entries * 32, 32):
        if not image[entry]:
            raise ValueError('OUTPUT.GZ no existe en la raiz FAT16')
        if image[entry:entry + 11] == OUTPUT_NAME:
            break
    else:
        raise ValueError('OUTPUT.GZ no existe en la raiz FAT16')
    cluster, size = struct.unpack_from('<HI', image, entry + 26)
    cluster_bytes = sector_size * sectors_per_cluster
    if not 0 < size <= 4 * cluster_bytes:
        raise ValueError('Tamano de OUTPUT.GZ fuera del perfil FAT16')
    chain = []
    for _ in range((size + cluster_bytes - 1) // cluster_bytes):
        if not 4 <= cluster <= 12 or cluster == 5 or cluster in chain:
            raise ValueError('Cadena FAT16 invalida')
        chain.append(cluster)
        cluster, mirror = (struct.unpack_from('<H', image, head + 2 * cluster)[0] for head in FAT_HEADS)
        if cluster != mirror:
            raise ValueError('Copias FAT16 distintas')
    if cluster < 0xfff8:
        raise ValueError('Cadena FAT16 sin marca de fin')
    offsets = [data + (cluster - 2) * cluster_bytes for cluster in chain]
    return entry, chain, offsets, size


def verify_output(initial, saved, *, replaced=False):
    entry, chain, offsets, size = output_layout(saved)
    if not replaced and (len(chain) < 2 or all(right == left + 1 for left, right in zip(chain, chain[1:]))):
        raise ValueError('El expediente debe usar una cadena FAT16 fragmentada')
    contents = b''.join(saved[offset:offset + SECTOR] for offset in offsets)[:size]
    expected = bytearray(initial)
    if replaced:
        old_entry, old_chain, _, _ = output_layout(initial)
        if old_entry != entry or set(old_chain) & set(chain):
            raise ValueError('El reemplazo debe conservar la entrada y usar otros clusters')
        for head in FAT_HEADS:
            for cluster in old_chain:
                struct.pack_into('<H', expected, head + 2 * cluster, 0)
    else:
        if expected[entry] != 0:
            raise ValueError('OUTPUT.GZ debe ocupar una entrada nueva')
        expected[entry:entry + 11] = OUTPUT_NAME
        expected[entry + 11] = 0x20
        struct.pack_into('<H', expected, entry + 24, 0x5d7b)
    struct.pack_into('<HI', expected, entry + 26, chain[0], size)
    for index, (cluster, offset) in enumerate(zip(chain, offsets)):
        following = chain[index + 1] if index + 1 < len(chain) else 0xffff
        for head in FAT_HEADS:
            if struct.unpack_from('<H', initial, head + 2 * cluster)[0]:
                raise ValueError('El archivo reutilizo un cluster ocupado')
            struct.pack_into('<H', expected, head + 2 * cluster, following)
        chunk = contents[index * SECTOR:(index + 1) * SECTOR]
        expected[offset:offset + SECTOR] = chunk.ljust(SECTOR, b'\0')
    if saved != expected:
        raise ValueError('La escritura FAT16 modifico bytes fuera de OUTPUT.GZ, su entrada y su cadena')
    return contents, chain, offsets


def exhaust_pool(image):
    saturated = bytearray(image)
    for head in FAT_HEADS:
        for cluster in range(4, 13):
            if not struct.unpack_from('<H', saturated, head + 2 * cluster)[0]:
                struct.pack_into('<H', saturated, head + 2 * cluster, 0xfff7)
    return saturated


def verify_interruption(initial, final, stopped, *, committed):
    entry, old_chain, _, old_size = output_layout(initial)
    new_entry, new_chain, offsets, new_size = output_layout(final)
    if new_entry != entry:
        raise ValueError('El reemplazo debe conservar la entrada FAT16')
    retained = bytearray(initial)
    for offset in offsets:
        retained[offset:offset + SECTOR] = final[offset:offset + SECTOR]
    expected = bytearray(retained)
    for head in FAT_HEADS if committed else FAT_HEADS[:1]:
        for cluster in new_chain:
            offset = head + 2 * cluster
            expected[offset:offset + 2] = final[offset:offset + 2]
    if committed:
        expected[entry:entry + 32] = final[entry:entry + 32]
    record = struct.pack('<4sII4s4s', b'BMJ1', old_size, new_size, bytes(old_chain), bytes(new_chain))
    record += struct.pack('<I', zlib.crc32(record))
    for offset in JOURNAL_COPIES:
        expected[offset:offset + SECTOR] = record.ljust(SECTOR, b'\0')
    if stopped != expected:
        raise ValueError('La imagen interrumpida difiere del punto de corte esperado')
    return final if committed else bytes(retained)


def tear_interruption(stopped, target, replacement_chain):
    image = bytearray(stopped)
    if target == 'fat':
        # One byte of the new end-of-chain marker reached the first FAT.
        offset = FAT_HEADS[0] + 2 * replacement_chain[-1]
        if image[offset:offset + 2] != b'\xff\xff':
            raise ValueError('El punto de corte no contiene la marca FAT esperada')
        image[offset + 1] = 0
    else:
        copies = {'primary': JOURNAL_COPIES[:1], 'secondary': JOURNAL_COPIES[1:], 'both': JOURNAL_COPIES}[target]
        for offset in copies:
            # The first 16 bytes reached the disk; the rest stayed clear.
            image[offset + 16:offset + SECTOR] = bytes(SECTOR - 16)
    return bytes(image)
