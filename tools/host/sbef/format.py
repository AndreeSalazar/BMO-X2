"""Read the provisional SBEF contract from bytes."""
import struct

from ..diagnostics import Rejection
from .isa import PROFILE_BY_ID, profile_id, profile_name, profile_requirements

PAGE = 4096
BASE = 0x40000000
END = BASE + 16 * 1024 * 1024
MAX_IMAGE = 1024 * 1024
MAX_REGIONS = 8
MACHINE = 62
FORMAT_VERSION = 2
LEGACY_FORMAT_VERSION = 1
HEADER = struct.Struct('<4sHHHHIQII')
REGION = struct.Struct('<QIIIIQ')
PERMISSIONS = {4: 'R', 5: 'RX', 6: 'RW'}


def image_limit(profile):
    if profile == 'default': return MAX_IMAGE
    if profile == 'rmlui-native-v1': return 2 * MAX_IMAGE
    raise ValueError('Unknown SBEF admission profile: '+profile)


def encode_header(abi, region_count, file_size, entry, *, isa_profile='x86-64-v1',
                  format_version=FORMAT_VERSION):
    if format_version not in (LEGACY_FORMAT_VERSION, FORMAT_VERSION):
        raise Rejection('SBEF-FORMAT-VERSION', 4, 'format_version')
    identifier = profile_id(isa_profile)
    if format_version == LEGACY_FORMAT_VERSION and identifier != 1:
        raise Rejection('SBEF-ISA-VERSION', 24, 'isa_profile')
    flags = 0 if format_version == LEGACY_FORMAT_VERSION else identifier
    return HEADER.pack(b'SBEF', format_version, abi, MACHINE, region_count,
                       file_size, entry, flags, 0)


def inspect(image, *, profile='default'):
    limit = image_limit(profile)
    if not HEADER.size <= len(image) <= limit:
        raise Rejection('SBEF-SIZE', min(len(image), limit), 'file')
    magic, version, abi, machine, count, size, entry, flags, reserved = HEADER.unpack_from(image)
    for value, expected, offset, field in [
            (magic, b'SBEF', 0, 'signature'), (machine, MACHINE, 8, 'architecture'),
            (reserved, 0, 28, 'reserved')]:
        if value != expected:
            raise Rejection('SBEF-HEADER', offset, field)
    if version == LEGACY_FORMAT_VERSION:
        if flags != 0:
            raise Rejection('SBEF-HEADER', 24, 'flags')
        isa_profile_id = 1
    elif version == FORMAT_VERSION:
        isa_profile_id = flags
        if isa_profile_id not in PROFILE_BY_ID:
            raise Rejection('SBEF-ISA-PROFILE', 24, 'isa_profile')
    else:
        raise Rejection('SBEF-HEADER', 4, 'format_version')
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
    if profile == 'rmlui-native-v1':
        expected = [('0x40000000', 'RX', 2*MAX_IMAGE), ('0x40200000', 'R', 2*MAX_IMAGE),
                    ('0x40400000', 'RW', 10*MAX_IMAGE)]
        if len(regions)!=3 or any((r['Address'],r['Permissions'])!=(a,p) or r['MappedBytes']>n
                                  for r,(a,p,n) in zip(regions,expected)):
            raise Rejection('SBEF-UI-LAYOUT', 32, 'regions')
    return dict(FormatVersion=version, AbiVersion=abi, Architecture='x86-64',
                IsaProfile=profile_name(isa_profile_id), IsaProfileId=isa_profile_id,
                IsaRequirements=profile_requirements(isa_profile_id), Bytes=size,
                Entry=f'0x{entry:X}', Regions=regions)
