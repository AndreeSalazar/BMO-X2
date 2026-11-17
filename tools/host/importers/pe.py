"""Inventory PE32+ and admit a fixed, single-region freestanding profile."""
import struct

from ..diagnostics import Rejection
from ..sbef.format import BASE, HEADER, MACHINE, PAGE, REGION, inspect


COFF = struct.Struct('<HHIIIHH')
SECTION = struct.Struct('<8sIIIIIIHHI')
SECTION_ALIGNMENT = 0x10000
DIRECTORIES = {
    1: ('imports', 'PE-IMPORTS'),
    3: ('exceptions', 'PE-EXCEPTIONS'),
    5: ('base_relocations', 'PE-RELOCATIONS'),
    6: ('debug', 'PE-DEBUG'),
    9: ('tls', 'PE-TLS'),
    13: ('delay_imports', 'PE-DELAY-IMPORTS'),
    14: ('clr', 'PE-CLR'),
}


def _inventory(data):
    if len(data) < 64 or data[:2] != b'MZ':
        raise Rejection('PE-DOS-HEADER', 0, 'e_magic')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if not 64 <= pe <= len(data) - 4 - COFF.size or data[pe:pe+4] != b'PE\0\0':
        raise Rejection('PE-SIGNATURE', 0x3c, 'e_lfanew')
    coff = pe + 4
    machine, count, _, _, _, opt_size, flags = COFF.unpack_from(data, coff)
    if machine != 0x8664:
        raise Rejection('PE-MACHINE', coff, 'Machine')
    if flags & 0x2000 or not flags & 2:
        raise Rejection('PE-IMAGE-KIND', coff + 18, 'Characteristics')
    opt = coff + COFF.size
    section_table = opt + opt_size
    if opt_size < 112 or section_table > len(data):
        raise Rejection('PE-OPTIONAL-SIZE', coff + 16, 'SizeOfOptionalHeader')
    if struct.unpack_from('<H', data, opt)[0] != 0x20b:
        raise Rejection('PE-OPTIONAL-MAGIC', opt, 'Magic')
    entry = struct.unpack_from('<I', data, opt + 16)[0]
    base = struct.unpack_from('<Q', data, opt + 24)[0]
    subsystem = struct.unpack_from('<H', data, opt + 68)[0]
    directory_count = struct.unpack_from('<I', data, opt + 108)[0]
    if directory_count > (opt_size - 112) // 8:
        raise Rejection('PE-DIRECTORY-COUNT', opt + 108, 'NumberOfRvaAndSizes')
    if not 1 <= count <= 96 or section_table + count * SECTION.size > len(data):
        raise Rejection('PE-SECTION-TABLE', coff + 2, 'NumberOfSections')

    sections = []
    for index in range(count):
        record = section_table + index * SECTION.size
        name, memsz, rva, filesz, offset, *_, perms = SECTION.unpack_from(data, record)
        if filesz and (offset > len(data) or filesz > len(data) - offset):
            raise Rejection('PE-SECTION-FILE-RANGE', record + 20, 'PointerToRawData', index)
        sections.append(dict(Name=name.split(b'\0', 1)[0].decode('ascii', errors='replace'),
                             RVA=rva, VirtualBytes=memsz, FileOffset=offset, FileBytes=filesz,
                             Readable=bool(perms & 0x40000000), Writable=bool(perms & 0x80000000),
                             Executable=bool(perms & 0x20000000)))
    blockers = []
    directories = {}
    for index in range(directory_count):
        name, code = DIRECTORIES.get(index, (f'directory_{index}', 'PE-UNSUPPORTED-DIRECTORY'))
        record = opt + 112 + index * 8
        rva, size = struct.unpack_from('<II', data, record)
        if rva or size:
            directories[name] = dict(RVA=rva, Bytes=size)
            if index not in (3, 6):
                blockers.append(Rejection(code, record, f'DataDirectory.{name}').report())
    result = dict(SourceFormat='PE32+', Architecture='x86-64', EntryRVA=entry, ImageBase=base,
                  Subsystem=subsystem, Sections=sections, Directories=directories,
                  CanPack=False, Blockers=blockers)
    return result, opt, section_table, flags


def _admit(data, result, opt, table, flags):
    sections = result['Sections']
    alignment, file_alignment = struct.unpack_from('<II', data, opt + 32)
    image_size, header_size = struct.unpack_from('<II', data, opt + 56)
    if (not flags & 1 or result['ImageBase'] != BASE - SECTION_ALIGNMENT or result['Subsystem'] != 3
            or alignment != SECTION_ALIGNMENT or file_alignment != 512 or image_size != 2 * SECTION_ALIGNMENT):
        raise Rejection('PE-FIXED-PROFILE', opt + 24, 'ImageBase/Alignment/SizeOfImage/Subsystem')
    if len(sections) != 1:
        raise Rejection('PE-REGION-COUNT', opt - 18, 'NumberOfSections')
    section = sections[0]
    rva, offset, size, raw = (section[k] for k in ('RVA', 'FileOffset', 'VirtualBytes', 'FileBytes'))
    if (section['Name'] != '.text' or not section['Readable'] or not section['Executable']
            or section['Writable']):
        raise Rejection('PE-PERMISSIONS', table + 36, 'Characteristics', 0)
    if (rva != SECTION_ALIGNMENT or not 0 < size <= raw <= PAGE or offset % file_alignment
            or raw % file_alignment or header_size % file_alignment
            or not table + SECTION.size <= header_size <= offset or offset + raw != len(data)):
        raise Rejection('PE-SECTION-LAYOUT', table + 8, 'VirtualSize/RVA/RawData', 0)
    if any(data[offset + size:offset + raw]):
        raise Rejection('PE-SECTION-PADDING', offset + size, 'RawData', 0)
    if not rva <= result['EntryRVA'] < rva + size:
        raise Rejection('PE-ENTRY', opt + 16, 'AddressOfEntryPoint')
    end = rva + size
    debug = result['Directories'].get('debug')
    if debug:
        start, length = debug['RVA'], debug['Bytes']
        if start % 4 or not length or length % 28 or not rva <= start < start + length <= end:
            raise Rejection('PE-DEBUG', opt + 160, 'DataDirectory.debug')
        for at in range(offset + start - rva, offset + start - rva + length, 28):
            kind, count, address, pointer = struct.unpack_from('<IIII', data, at + 12)
            if (kind not in (13, 16) or (count and
                    (not rva <= address < address + count <= end or pointer != offset + address - rva))
                    or (not count and (address or pointer))):
                raise Rejection('PE-DEBUG-RECORD', at, 'IMAGE_DEBUG_DIRECTORY')
    exceptions = result['Directories'].get('exceptions')
    if exceptions:
        start, length = exceptions['RVA'], exceptions['Bytes']
        if start % 4 or not length or length % 12 or not rva <= start < start + length <= end:
            raise Rejection('PE-EXCEPTIONS', opt + 136, 'DataDirectory.exceptions')
        previous_end = rva
        for at in range(offset + start - rva, offset + start - rva + length, 12):
            begin, finish, unwind = struct.unpack_from('<III', data, at)
            if not previous_end <= begin < finish <= end or unwind % 4 or not rva <= unwind <= end - 4:
                raise Rejection('PE-UNWIND-RANGE', at, 'RUNTIME_FUNCTION')
            info = offset + unwind - rva
            version_flags, prolog, slots, _ = struct.unpack_from('<BBBB', data, info)
            if version_flags != 1 or prolog > finish - begin or unwind + 4 + ((slots + 1) & ~1) * 2 > end:
                raise Rejection('PE-UNWIND-INFO', info, 'UNWIND_INFO')
            previous_end = finish
    return data[offset:offset + size]


def probe_pe(data):
    result, opt, table, flags = _inventory(data)
    if not result['Blockers']:
        try:
            _admit(data, result, opt, table, flags)
        except Rejection as error:
            result['Blockers'].append(error.report())
    result['CanPack'] = not result['Blockers']
    return result


def pack_pe(data, *, abi):
    result, opt, table, flags = _inventory(data)
    if result['Blockers']:
        blocker = result['Blockers'][0]
        raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    payload = _admit(data, result, opt, table, flags)
    if abi != 1:
        raise Rejection('PE-ABI', 0, 'abi_version')
    offset = HEADER.size + REGION.size
    image = HEADER.pack(b'SBEF', 1, abi, MACHINE, 1, offset + len(payload),
                        result['ImageBase'] + result['EntryRVA'], 0, 0)
    image += REGION.pack(BASE, offset, len(payload), len(payload), 5, 0) + payload
    inspect(image)
    return image
