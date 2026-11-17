"""Inventory PE32+ and admit fixed-address freestanding profiles."""
import struct

from ..diagnostics import Rejection
from ..sbef.format import BASE, HEADER, MACHINE, MAX_IMAGE, PAGE, REGION, inspect
from .pe_imports import inventory_imports
from .pe_bindings import bind_session_clock


COFF = struct.Struct('<HHIIIHH')
SECTION = struct.Struct('<8sIIIIIIHHI')
SECTION_ALIGNMENT = 0x10000
SEPARATE_ALIGNMENT = 0x200000
DIRECTORIES = {
    1: ('imports', 'PE-IMPORTS'),
    3: ('exceptions', 'PE-EXCEPTIONS'),
    5: ('base_relocations', 'PE-RELOCATIONS'),
    6: ('debug', 'PE-DEBUG'),
    9: ('tls', 'PE-TLS'),
    11: ('bound_imports', 'PE-BOUND-IMPORTS'),
    12: ('iat', 'PE-IAT'),
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
    _metadata(data, result, opt, section, section)
    return [(BASE, data[offset:offset + size], size, 5)]


def _metadata(data, result, opt, text, readonly):
    rva, offset, size = (readonly[k] for k in ('RVA', 'FileOffset', 'VirtualBytes'))
    end = rva + min(size, readonly['FileBytes'])
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
        code_start = text['RVA']
        code_end = code_start + min(text['VirtualBytes'], text['FileBytes'])
        previous_end = code_start
        for at in range(offset + start - rva, offset + start - rva + length, 12):
            begin, finish, unwind = struct.unpack_from('<III', data, at)
            if not previous_end <= begin < finish <= code_end or unwind % 4 or not rva <= unwind <= end - 4:
                raise Rejection('PE-UNWIND-RANGE', at, 'RUNTIME_FUNCTION')
            info = offset + unwind - rva
            version_flags, prolog, slots, _ = struct.unpack_from('<BBBB', data, info)
            if version_flags != 1 or prolog > finish - begin or unwind + 4 + ((slots + 1) & ~1) * 2 > end:
                raise Rejection('PE-UNWIND-INFO', info, 'UNWIND_INFO')
            previous_end = finish


def _admit_separate(data, result, opt, table, flags):
    alignment, file_alignment = struct.unpack_from('<II', data, opt + 32)
    image_size, header_size = struct.unpack_from('<II', data, opt + 56)
    if (not flags & 1 or result['Subsystem'] != 3 or alignment != SEPARATE_ALIGNMENT
            or file_alignment != 512 or image_size != 4 * alignment):
        raise Rejection('PE-FIXED-PROFILE', opt + 24, 'ImageBase/Alignment/SizeOfImage/Subsystem')
    sections = result['Sections']
    if len(sections) != 3:
        raise Rejection('PE-REGION-COUNT', opt - 18, 'NumberOfSections')
    if not table + 3 * SECTION.size <= header_size <= len(data) or header_size % file_alignment:
        raise Rejection('PE-OPTIONAL-SIZE', opt + 60, 'SizeOfHeaders')
    file_cursor = header_size
    segments = []
    for index, (section, (name, permissions)) in enumerate(zip(sections, (
        ('.text', 5), ('.rdata', 4), ('.data', 6),
    ))):
        record = table + SECTION.size * index
        actual = (4 * section['Readable'] + 2 * section['Writable'] + section['Executable'])
        if section['Name'] != name or actual != permissions:
            raise Rejection('PE-PERMISSIONS', record + 36, 'Characteristics', index)
        rva, offset, size, raw = (section[k] for k in ('RVA', 'FileOffset', 'VirtualBytes', 'FileBytes'))
        # The linked image reserves a 2 MiB slot for each section.
        if (rva != (index + 1) * alignment or not 0 < size <= alignment
                or (permissions != 6 and raw < size)):
            raise Rejection('PE-SECTION-LAYOUT', record + 8, 'VirtualSize/RVA', index)
        if raw:
            if offset != file_cursor or raw % file_alignment:
                raise Rejection('PE-SECTION-LAYOUT', record + 16, 'RawData', index)
            if any(data[offset + min(size, raw):offset + raw]):
                raise Rejection('PE-SECTION-PADDING', offset + size, 'RawData', index)
            file_cursor += raw
        elif offset or permissions != 6:
            raise Rejection('PE-SECTION-LAYOUT', record + 16, 'RawData', index)
        segments.append((result['ImageBase'] + rva, data[offset:offset + min(size, raw)], size, permissions))
    if file_cursor != len(data):
        raise Rejection('PE-TRAILING-DATA', file_cursor, 'RawData')
    text = sections[0]
    if not text['RVA'] <= result['EntryRVA'] < text['RVA'] + len(segments[0][1]):
        raise Rejection('PE-ENTRY', opt + 16, 'AddressOfEntryPoint')
    _metadata(data, result, opt, text, sections[1])
    return segments


def _regions(data, result, opt, table, flags):
    if result['ImageBase'] == BASE - SEPARATE_ALIGNMENT:
        segments = _admit_separate(data, result, opt, table, flags)
    else:
        segments = _admit(data, result, opt, table, flags)
    total = HEADER.size + REGION.size * len(segments) + sum(len(payload) for _, payload, _, _ in segments)
    if total > MAX_IMAGE:
        raise Rejection('PE-OUTPUT-SIZE', opt + 56, 'SizeOfImage', actual=total, limit=MAX_IMAGE)
    return segments, total


def probe_pe(data):
    result, opt, table, flags = _inventory(data)
    imports = result['Directories'].get('imports')
    if imports:
        try:
            result['Imports'] = inventory_imports(data, result['Sections'], imports, opt + 120)
        except Rejection as error:
            result['ImportInventoryError'] = error.report()
    if not result['Blockers']:
        try:
            _regions(data, result, opt, table, flags)
        except Rejection as error:
            result['Blockers'].append(error.report())
    result['CanPack'] = not result['Blockers']
    return result


def pack_pe(data, *, abi, clock_target=None):
    result, opt, table, flags = _inventory(data)
    blockers = [b for b in result['Blockers']
                if clock_target is None or b['Code'] not in ('PE-IMPORTS', 'PE-IAT')]
    if blockers:
        blocker = blockers[0]
        raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    segments, total = _regions(data, result, opt, table, flags)
    if abi != 1:
        raise Rejection('PE-ABI', 0, 'abi_version')
    if clock_target is not None:
        if len(segments) != 3:
            raise Rejection('PE-CLOCK-PROFILE', opt + 24, 'ImageBase')
        bind_session_clock(data, result, opt, segments, clock_target)
    offset = HEADER.size + REGION.size * len(segments)
    table_bytes = bytearray()
    for address, payload, size, permissions in segments:
        table_bytes.extend(REGION.pack(address, offset, len(payload), size, permissions, 0))
        offset += len(payload)
    image = HEADER.pack(b'SBEF', 1, abi, MACHINE, len(segments), total,
                        result['ImageBase'] + result['EntryRVA'], 0, 0)
    image += table_bytes + b''.join(payload for _, payload, _, _ in segments)
    inspect(image)
    return image
