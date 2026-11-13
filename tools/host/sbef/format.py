"""Read the provisional SBEF contract from bytes."""
import struct

from ..diagnostics import Rejection

PAGE = 4096
BASE = 0x40000000
END = BASE + 16 * 1024 * 1024
MAX_IMAGE = 1024 * 1024
MAX_REGIONS = 8
MACHINE = 62
HEADER = struct.Struct('<4sHHHHIQII')
REGION = struct.Struct('<QIIIIQ')
PERMISSIONS = {4: 'R', 5: 'RX', 6: 'RW'}


def inspect(image):
    if not HEADER.size <= len(image) <= MAX_IMAGE:
        raise Rejection('SBEF-SIZE', min(len(image), MAX_IMAGE), 'file')
    magic, version, abi, machine, count, size, entry, flags, reserved = HEADER.unpack_from(image)
    for value, expected, offset, field in [
            (magic, b'SBEF', 0, 'signature'), (version, 1, 4, 'format_version'),
            (machine, MACHINE, 8, 'architecture'),
            (flags, 0, 24, 'flags'), (reserved, 0, 28, 'reserved')]:
        if value != expected:
            raise Rejection('SBEF-HEADER', offset, field)
    if abi not in (0, 1):
        raise Rejection('SBEF-HEADER', 6, 'abi_version')
    cursor = HEADER.size + count * REGION.size
    if not 1 <= count <= MAX_REGIONS or cursor > len(image):
        raise Rejection('SBEF-TABLE', 10, 'region_count')
    if size != len(image):
        raise Rejection('SBEF-SIZE', 12, 'file_size')

    previous_end = BASE
    entry_in_text = False
    regions = []
    for index in range(count):
        record = HEADER.size + index * REGION.size
        address, offset, filesz, memsz, perms, reserved = REGION.unpack_from(image, record)
        if reserved:
            raise Rejection('SBEF-REGION', record + 24, 'reserved', index)
        if perms not in PERMISSIONS:
            raise Rejection('SBEF-PERMISSIONS', record + 20, 'permissions', index)
        if not memsz or filesz > memsz:
            raise Rejection('SBEF-REGION', record + 16, 'memory_size', index)
        end = address + ((memsz + PAGE - 1) // PAGE) * PAGE
        if address % PAGE or not previous_end <= address < end <= END:
            raise Rejection('SBEF-VIRTUAL-RANGE', record, 'virtual_address', index)
        if offset != cursor:
            raise Rejection('SBEF-FILE-RANGE', record + 8, 'file_offset', index)
        if filesz > size - cursor:
            raise Rejection('SBEF-FILE-RANGE', record + 12, 'file_size', index)
        cursor += filesz
        previous_end = end
        entry_in_text |= perms == 5 and address <= entry < address + filesz
        regions.append(dict(Address=f'0x{address:X}', Offset=offset, FileBytes=filesz, MemoryBytes=memsz,
                            MappedBytes=end-address, Permissions=PERMISSIONS[perms]))
    if cursor != size:
        raise Rejection('SBEF-TRAILING-DATA', cursor, 'payload')
    if not entry_in_text:
        raise Rejection('SBEF-ENTRY', 16, 'entry')
    return dict(FormatVersion=version, AbiVersion=abi, Architecture='x86-64', Bytes=size,
                Entry=f'0x{entry:X}', Regions=regions)
