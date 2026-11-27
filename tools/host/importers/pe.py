"""Inventory PE32+ and admit fixed-address freestanding profiles."""
import struct

from ..diagnostics import Rejection
from ..sbef.format import (BASE, END, FORMAT_VERSION, HEADER, MACHINE, MAX_IMAGE,
                           PAGE, REGION, encode_header, inspect)
from .pe_imports import inventory_imports
from .pe_load_config import inventory_load_config
from .pe_bindings import bind_fixed_imports, bind_session_imports
from .pe_exports import (DLL_ENTRY_EXPORT, DLL_LIFECYCLE_BASE, DLL_LIFECYCLE_PROFILE,
                         FIXED_DLL_PROFILE, code_exports)
from .pe_tls import TLS_PROFILE, tls_regions
from .pe_unwind import inventory_unwind


COFF = struct.Struct('<HHIIIHH')
SECTION = struct.Struct('<8sIIIIIIHHI')
SECTION_ALIGNMENT = 0x10000
SEPARATE_ALIGNMENT = 0x200000
DIRECTORIES = {
    0: ('exports', 'PE-EXPORTS'),
    1: ('imports', 'PE-IMPORTS'),
    2: ('resources', 'PE-RESOURCES'),
    3: ('exceptions', 'PE-EXCEPTIONS'),
    4: ('security', 'PE-SECURITY'),
    5: ('base_relocations', 'PE-RELOCATIONS'),
    6: ('debug', 'PE-DEBUG'),
    7: ('architecture', 'PE-ARCHITECTURE'),
    8: ('global_pointer', 'PE-GLOBAL-POINTER'),
    9: ('tls', 'PE-TLS'),
    10: ('load_config', 'PE-LOAD-CONFIG'),
    11: ('bound_imports', 'PE-BOUND-IMPORTS'),
    12: ('iat', 'PE-IAT'),
    13: ('delay_imports', 'PE-DELAY-IMPORTS'),
    14: ('clr', 'PE-CLR'),
    15: ('reserved', 'PE-RESERVED'),
}


def _inventory(data, *, allow_x86=False):
    if len(data) < 64 or data[:2] != b'MZ':
        raise Rejection('PE-DOS-HEADER', 0, 'e_magic')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if not 64 <= pe <= len(data) - 4 - COFF.size or data[pe:pe+4] != b'PE\0\0':
        raise Rejection('PE-SIGNATURE', 0x3c, 'e_lfanew')
    coff = pe + 4
    machine, count, _, _, _, opt_size, flags = COFF.unpack_from(data, coff)
    x86 = machine == 0x14c and allow_x86
    if machine != 0x8664 and not x86:
        raise Rejection('PE-MACHINE', coff, 'Machine')
    if not flags & 2:
        raise Rejection('PE-IMAGE-KIND', coff + 18, 'Characteristics')
    opt = coff + COFF.size
    section_table = opt + opt_size
    directories_offset = 96 if x86 else 112
    if opt_size < directories_offset or section_table > len(data):
        raise Rejection('PE-OPTIONAL-SIZE', coff + 16, 'SizeOfOptionalHeader')
    if struct.unpack_from('<H', data, opt)[0] != (0x10b if x86 else 0x20b):
        raise Rejection('PE-OPTIONAL-MAGIC', opt, 'Magic')
    entry = struct.unpack_from('<I', data, opt + 16)[0]
    base = struct.unpack_from('<I' if x86 else '<Q', data, opt + (28 if x86 else 24))[0]
    subsystem = struct.unpack_from('<H', data, opt + 68)[0]
    dll_characteristics = struct.unpack_from('<H', data, opt + 70)[0]
    section_alignment, file_alignment = struct.unpack_from('<II', data, opt + 32)
    image_size, header_size = struct.unpack_from('<II', data, opt + 56)
    directory_count = struct.unpack_from('<I', data, opt + directories_offset - 4)[0]
    if directory_count > (opt_size - directories_offset) // 8:
        raise Rejection('PE-DIRECTORY-COUNT', opt + directories_offset - 4, 'NumberOfRvaAndSizes')
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
                             Executable=bool(perms & 0x20000000), Characteristics=perms))
    is_dll = bool(flags & 0x2000)
    blockers = ([Rejection('PE-IMAGE-KIND', coff + 18, 'Characteristics').report()]
                if is_dll else [])
    if x86:
        blockers.insert(0, Rejection('PE-MACHINE', coff, 'Machine').report())
    directories = {}
    for index in range(directory_count):
        name, code = DIRECTORIES.get(index, (f'directory_{index}', 'PE-UNSUPPORTED-DIRECTORY'))
        record = opt + directories_offset + index * 8
        rva, size = struct.unpack_from('<II', data, record)
        if rva or size:
            directories[name] = dict(RVA=rva, Bytes=size)
            if index not in (3, 5, 6):
                blockers.append(Rejection(code, record, f'DataDirectory.{name}').report())
    result = dict(SourceFormat='PE32' if x86 else 'PE32+', Architecture='x86' if x86 else 'x86-64',
                  EntryRVA=entry, ImageBase=base,
                  ImageKind='DLL' if is_dll else 'EXE', Subsystem=subsystem,
                  DllCharacteristics=dll_characteristics, SectionAlignment=section_alignment,
                  FileAlignment=file_alignment, ImageSize=image_size, HeaderSize=header_size,
                  Sections=sections, Directories=directories,
                  CanPack=False, Blockers=blockers)
    return result, opt, section_table, flags


def _section_memory_size(section):
    return section['VirtualBytes'] or section['FileBytes']


def _base_relocations(data, result, opt):
    directory = result['Directories'].get('base_relocations')
    if not directory:
        return []

    matches = []
    for index, section in enumerate(result['Sections']):
        delta = directory['RVA'] - section['RVA']
        memory_size = _section_memory_size(section)
        file_backed = min(memory_size, section['FileBytes'])
        if (0 <= delta and delta + directory['Bytes'] <= file_backed
                and directory['RVA'] + directory['Bytes'] <= section['RVA'] + memory_size):
            matches.append((index, section['FileOffset'] + delta))
    if len(matches) != 1 or directory['Bytes'] < 8:
        raise Rejection('PE-RELOCATION-DIRECTORY', opt + 152, 'DataDirectory.base_relocations')

    _, start = matches[0]
    end = start + directory['Bytes']
    entries = []
    cursor = start
    while cursor < end:
        if not any(data[cursor:end]):
            break
        if cursor + 8 > end:
            raise Rejection('PE-RELOCATION-BLOCK', cursor, 'SizeOfBlock')
        page_rva, block_size = struct.unpack_from('<II', data, cursor)
        if (page_rva % PAGE or page_rva >= result['ImageSize'] or block_size < 8
                or block_size % 4 or block_size > end - cursor):
            raise Rejection('PE-RELOCATION-BLOCK', cursor, 'SizeOfBlock')
        for at in range(cursor + 8, cursor + block_size, 2):
            value, = struct.unpack_from('<H', data, at)
            kind, offset = value >> 12, value & 0xfff
            if kind == 0:
                continue
            if kind != 10:
                raise Rejection('PE-RELOCATION-TYPE', at, 'Type')
            if offset > PAGE - 8:
                raise Rejection('PE-RELOCATION-TARGET', at, 'VirtualAddress')
            target = page_rva + offset
            target_sections = []
            for index, section in enumerate(result['Sections']):
                if section['RVA'] <= target and target + 8 <= section['RVA'] + _section_memory_size(section):
                    target_sections.append((index, target - section['RVA']))
            if len(target_sections) != 1:
                raise Rejection('PE-RELOCATION-TARGET', at, 'VirtualAddress')
            index, target_offset = target_sections[0]
            section = result['Sections'][index]
            value_bytes = bytearray(8)
            backed = min(section['FileBytes'], _section_memory_size(section)) - target_offset
            if backed > 0:
                amount = min(8, backed)
                source = section['FileOffset'] + target_offset
                value_bytes[:amount] = data[source:source + amount]
            value = struct.unpack('<Q', value_bytes)[0]
            entries.append((target, index, target_offset, value, at))
        cursor += block_size
    return entries


def _admit_relocated(data, result, opt, table, flags, relocations, *, load_base=BASE, library=False):
    sections = result['Sections']
    image_size = result['ImageSize']
    section_alignment = result['SectionAlignment']
    file_alignment = result['FileAlignment']
    header_size = result['HeaderSize']
    if result['ImageKind'] != ('DLL' if library else 'EXE'):
        raise Rejection('PE-IMAGE-KIND', opt - 18, 'Characteristics')
    if result['Subsystem'] != 3:
        raise Rejection('PE-SUBSYSTEM', opt + 68, 'Subsystem')
    if (not PAGE <= section_alignment <= 0x100000
            or section_alignment & (section_alignment - 1) or section_alignment % PAGE):
        raise Rejection('PE-SECTION-ALIGNMENT', opt + 32, 'SectionAlignment')
    if (not 512 <= file_alignment <= 65536 or file_alignment & (file_alignment - 1)
            or file_alignment > section_alignment):
        raise Rejection('PE-FILE-ALIGNMENT', opt + 36, 'FileAlignment')
    if (image_size <= header_size or image_size % section_alignment
            or image_size > 16 * 1024 * 1024
            or load_base + image_size > END):
        raise Rejection('PE-IMAGE-LAYOUT', opt + 56, 'SizeOfImage')
    if (header_size % file_alignment or header_size > len(data)
            or table + len(sections) * SECTION.size > header_size):
        raise Rejection('PE-HEADERS', opt + 60, 'SizeOfHeaders')
    if result['ImageBase'] % 0x10000 or result['ImageBase'] + image_size > (1 << 64):
        raise Rejection('PE-IMAGE-BASE', opt + 24, 'ImageBase')
    if not 1 <= len(sections) <= 8:
        raise Rejection('PE-REGION-COUNT', opt - 18, 'NumberOfSections')

    previous_page_end = 0
    raw_ranges = []
    regions = []
    buffers = []
    entry_executable = False
    for index, section in enumerate(sections):
        rva = section['RVA']
        virtual_size = _section_memory_size(section)
        raw_size = section['FileBytes']
        raw_offset = section['FileOffset']
        if (not virtual_size or rva % section_alignment or rva < header_size
                or rva > image_size or virtual_size > image_size - rva
                or rva % PAGE or raw_size and (raw_offset % file_alignment
                or raw_size % file_alignment or raw_offset < header_size)):
            raise Rejection('PE-SECTION-LAYOUT', table + index * SECTION.size + 8,
                            'VirtualAddress/SizeOfRawData', index)
        mapped_end = rva + ((virtual_size + PAGE - 1) // PAGE) * PAGE
        if rva < previous_page_end or mapped_end > image_size:
            raise Rejection('PE-SECTION-OVERLAP', table + index * SECTION.size + 8,
                            'VirtualAddress', index)
        previous_page_end = mapped_end
        if raw_size:
            if raw_offset > len(data) or raw_size > len(data) - raw_offset:
                raise Rejection('PE-SECTION-FILE-RANGE', table + index * SECTION.size + 20,
                                'PointerToRawData', index)
            raw_ranges.append((raw_offset, raw_offset + raw_size, index))
        if section['VirtualBytes'] and raw_size > virtual_size and any(
                data[raw_offset + virtual_size:raw_offset + raw_size]):
            raise Rejection('PE-SECTION-PADDING', raw_offset + virtual_size, 'RawData', index)
        if not section['Readable'] or section['Writable'] and section['Executable']:
            raise Rejection('PE-PERMISSIONS', table + index * SECTION.size + 36,
                            'Characteristics', index)
        permissions = 6 if section['Writable'] else 5 if section['Executable'] else 4
        buffer = bytearray(virtual_size)
        copy_size = min(raw_size, virtual_size)
        entry_executable |= (section['Executable'] and rva <= result['EntryRVA'] < rva + copy_size)
        if copy_size:
            buffer[:copy_size] = data[raw_offset:raw_offset + copy_size]
        buffers.append(buffer)
        regions.append([load_base + rva, buffer, virtual_size, permissions, copy_size])
    if not library and not entry_executable:
        raise Rejection('PE-ENTRY', opt + 16, 'AddressOfEntryPoint')
    raw_ranges.sort()
    file_cursor = header_size
    for start, end, index in raw_ranges:
        if start < file_cursor:
            raise Rejection('PE-SECTION-FILE-OVERLAP', table + index * SECTION.size + 20,
                            'PointerToRawData', index)
        if any(data[file_cursor:start]):
            raise Rejection('PE-SECTION-FILE-GAP', file_cursor, 'RawData', index)
        file_cursor = end
    if any(data[file_cursor:]):
        raise Rejection('PE-TRAILING-DATA', file_cursor, 'RawData')

    delta = load_base - result['ImageBase']
    if delta and not relocations:
        raise Rejection('PE-RELOCATIONS-MISSING', opt + 24, 'ImageBase')
    if delta and flags & 1:
        raise Rejection('PE-RELOCATIONS-STRIPPED', opt + 24, 'Characteristics.RELOCS_STRIPPED')
    if delta and not result['DllCharacteristics'] & 0x40:
        raise Rejection('PE-REBASE-FLAG', opt + 70, 'DllCharacteristics.DYNAMIC_BASE')
    seen = set()
    for target, index, target_offset, value, record in relocations:
        if target in seen:
            raise Rejection('PE-RELOCATION-DUPLICATE', record, 'VirtualAddress')
        seen.add(target)
        target_rva = value - result['ImageBase']
        if not any(section['RVA'] <= target_rva < section['RVA'] + _section_memory_size(section)
                   for section in sections):
            raise Rejection('PE-RELOCATION-VALUE', record, 'DIR64')
        relocated = value + delta
        if not load_base <= relocated < load_base + image_size:
            raise Rejection('PE-RELOCATION-VALUE', record, 'DIR64')
        struct.pack_into('<Q', buffers[index], target_offset, relocated)
        regions[index][4] = max(regions[index][4], target_offset + 8)
    return [(address, bytes(buffer[:file_size]), mem_size, permissions)
            for address, buffer, mem_size, permissions, file_size in regions]


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
    padding = data[offset + size:offset + raw]
    # MSVC uses zero fill, while LLD uses INT3 fill for executable sections.
    # Raw padding is outside VirtualSize and never enters the SBEF segment.
    if any(padding) and padding != b'\xcc' * len(padding):
        raise Rejection('PE-SECTION-PADDING', offset + size, 'RawData', 0)
    if not rva <= result['EntryRVA'] < rva + size:
        raise Rejection('PE-ENTRY', opt + 16, 'AddressOfEntryPoint')
    _metadata(data, result, opt, section, section)
    return [(BASE, data[offset:offset + size], size, 5)]


def _metadata(data, result, opt, text, readonly, *, fixture_handlers=()):
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
        seen_handlers = set()
        prior_functions = set()
        for at in range(offset + start - rva, offset + start - rva + length, 12):
            begin, finish, unwind = struct.unpack_from('<III', data, at)
            if not previous_end <= begin < finish <= code_end or unwind % 4 or not rva <= unwind <= end - 4:
                raise Rejection('PE-UNWIND-RANGE', at, 'RUNTIME_FUNCTION')
            info = offset + unwind - rva
            version_flags, prolog, slots, _ = struct.unpack_from('<BBBB', data, info)
            tail = unwind + 4 + ((slots + 1) & ~1) * 2
            if (version_flags & 7) != 1 or prolog > finish - begin or tail > end:
                raise Rejection('PE-UNWIND-INFO', info, 'UNWIND_INFO')
            flags = version_flags >> 3
            if flags == 4 and fixture_handlers:
                if tail + 12 > end or struct.unpack_from('<III', data, offset + tail - rva) not in prior_functions:
                    raise Rejection('PE-UNWIND-GS-CHAIN', offset + tail - rva, 'ChainedRuntimeFunction')
            elif flags:
                if not fixture_handlers or flags not in (1, 2, 3) or tail + 8 > end:
                    raise Rejection('PE-UNWIND-INFO', info, 'UNWIND_INFO')
                handler, = struct.unpack_from('<I', data, offset + tail - rva)
                if handler not in fixture_handlers or not code_start <= handler < code_end:
                    raise Rejection('PE-UNWIND-GS-HANDLER', offset + tail - rva, 'ExceptionHandler')
                seen_handlers.add(handler)
            if fixture_handlers:
                prior_functions.add((begin, finish, unwind))
            previous_end = finish
        if seen_handlers != set(fixture_handlers):
            raise Rejection('PE-UNWIND-GS-HANDLER', opt + 136, 'DataDirectory.exceptions')


def _validate_generic_debug(data, result, opt, table, *, library=False):
    debug = result['Directories'].get('debug')
    if not debug:
        return
    start, length = debug['RVA'], debug['Bytes']
    matches = [section for section in result['Sections']
               if section['RVA'] <= start
               and start + length <= section['RVA'] + min(
                   _section_memory_size(section), section['FileBytes'])]
    entries = [section for section in result['Sections']
               if section['Executable'] and section['RVA'] <= result['EntryRVA']
               < section['RVA'] + min(_section_memory_size(section), section['FileBytes'])]
    if len(matches) != 1 or (not library and len(entries) != 1) or matches[0]['Writable']:
        raise Rejection('PE-DEBUG-PENDING', opt + 160, 'DataDirectory.debug')
    _metadata(data, result, opt, None if library else entries[0], matches[0])


def _admit_separate(data, result, opt, table, flags, *, fixture_handlers=()):
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
    _metadata(data, result, opt, text, sections[1], fixture_handlers=fixture_handlers)
    return segments


def _regions(data, result, opt, table, flags):
    relocations = _base_relocations(data, result, opt)
    if result['ImageBase'] == BASE - SEPARATE_ALIGNMENT:
        if result['Directories'].get('base_relocations'):
            raise Rejection('PE-FIXED-RELOCATIONS', opt + 152, 'DataDirectory.base_relocations')
        segments = _admit_separate(data, result, opt, table, flags)
    elif result['ImageBase'] == BASE - SECTION_ALIGNMENT:
        if result['Directories'].get('base_relocations'):
            raise Rejection('PE-FIXED-RELOCATIONS', opt + 152, 'DataDirectory.base_relocations')
        segments = _admit(data, result, opt, table, flags)
    else:
        if result['Directories'].get('exceptions'):
            raise Rejection('PE-EXCEPTIONS-PENDING', opt + 136, 'DataDirectory.exceptions')
        _validate_generic_debug(data, result, opt, table)
        segments = _admit_relocated(data, result, opt, table, flags, relocations)
    total = HEADER.size + REGION.size * len(segments) + sum(len(payload) for _, payload, _, _ in segments)
    if total > MAX_IMAGE:
        raise Rejection('PE-OUTPUT-SIZE', opt + 56, 'SizeOfImage', actual=total, limit=MAX_IMAGE)
    return segments, total


def probe_pe(data):
    result, opt, table, flags = _inventory(data, allow_x86=True)
    x86 = result['Architecture'] == 'x86'
    imports = result['Directories'].get('imports')
    if imports:
        try:
            result['Imports'] = inventory_imports(
                data, result['Sections'], imports, opt + (104 if x86 else 120), x86=x86)
        except Rejection as error:
            result['ImportInventoryError'] = error.report()
    if x86:
        return result
    exceptions = result['Directories'].get('exceptions')
    if exceptions:
        try:
            result['UnwindInventory'] = inventory_unwind(data, result['Sections'], exceptions, opt + 136)
        except Rejection as error:
            result['UnwindInventoryError'] = error.report()
    load_config = result['Directories'].get('load_config')
    if load_config:
        try:
            result['LoadConfigInventory'] = inventory_load_config(
                data, result['Sections'], load_config, result['ImageBase'], opt + 192)
        except Rejection as error:
            result['LoadConfigInventoryError'] = error.report()
    try:
        relocations = _base_relocations(data, result, opt)
        result['Relocations'] = dict(Count=len(relocations), Types=['DIR64'] if relocations else [],
                                     TargetLoadBase=f'0x{BASE:X}')
    except Rejection as error:
        result['RelocationInventoryError'] = error.report()
        result['Blockers'].append(error.report())
    if not result['Blockers']:
        try:
            _regions(data, result, opt, table, flags)
        except Rejection as error:
            result['Blockers'].append(error.report())
    result['CanPack'] = not result['Blockers']
    return result


def pack_pe(data, *, abi, bindings=None, isa_profile='x86-64-v1',
            format_version=FORMAT_VERSION):
    result, opt, table, flags = _inventory(data)
    blockers = [b for b in result['Blockers']
                if bindings is None or b['Code'] not in ('PE-IMPORTS', 'PE-IAT')]
    if blockers:
        blocker = blockers[0]
        raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    segments, _ = _regions(data, result, opt, table, flags)
    if abi != 1:
        raise Rejection('PE-ABI', 0, 'abi_version')
    if bindings is not None:
        if len(segments) != 3:
            raise Rejection('PE-SESSION-PROFILE', opt + 24, 'ImageBase')
        bind_session_imports(data, result, opt, segments, bindings)
    if result['ImageBase'] in (BASE - SECTION_ALIGNMENT, BASE - SEPARATE_ALIGNMENT):
        entry = result['ImageBase'] + result['EntryRVA']
    else:
        entry = BASE + result['EntryRVA']
    return _encode_pe_segments(segments, abi, entry, isa_profile, format_version)


def pack_pe_gs_fixture(data, handler_rva, *, seh_handler_rva=None):
    """Package the locally built /GS QEMU fixture in the abort-only fault profile."""
    result, opt, table, flags = _inventory(data)
    if result['Blockers']:
        blocker = result['Blockers'][0]
        raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    if result['ImageBase'] != BASE - SEPARATE_ALIGNMENT or 'exceptions' not in result['Directories']:
        raise Rejection('PE-UNWIND-GS-FIXTURE', opt + 24, 'ImageBase/DataDirectory.exceptions')
    handlers = (handler_rva,) if seh_handler_rva is None else (handler_rva, seh_handler_rva)
    segments = _admit_separate(data, result, opt, table, flags, fixture_handlers=handlers)
    return _encode_pe_segments(segments, 1, result['ImageBase'] + result['EntryRVA'], 'x86-64-v1', FORMAT_VERSION)


def _encode_pe_segments(segments, abi, entry, isa_profile, format_version):
    offset = HEADER.size + REGION.size * len(segments)
    table_bytes = bytearray()
    for address, payload, size, permissions in segments:
        table_bytes.extend(REGION.pack(address, offset, len(payload), size, permissions, 0))
        offset += len(payload)
    image = encode_header(abi, len(segments), offset, entry,
                          isa_profile=isa_profile, format_version=format_version)
    image += table_bytes + b''.join(payload for _, payload, _, _ in segments)
    inspect(image)
    return image


def pack_pe_tls(data, *, abi, isa_profile='x86-64-v1', format_version=FORMAT_VERSION):
    result, opt, table, flags = _inventory(data)
    for blocker in result['Blockers']:
        if blocker['Code'] != 'PE-TLS':
            raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    if (abi != TLS_PROFILE['AbiVersion'] or format_version != FORMAT_VERSION
            or result['ImageBase'] != BASE - SEPARATE_ALIGNMENT or 'base_relocations' in result['Directories']):
        raise Rejection('PE-TLS-PROFILE', opt + 24, 'SBEF v2 ABI 1 / EXE.ImageBase')
    executable = _admit_separate(data, result, opt, table, flags)
    tls, report = tls_regions(result, executable, opt)
    return _encode_pe_segments(executable + tls, abi, result['ImageBase'] + result['EntryRVA'],
                               isa_profile, format_version), report


def pack_pe_with_dll(data, dll, *, abi, isa_profile='x86-64-v1', format_version=FORMAT_VERSION, lifecycle=False):
    """Bind one fixed Win64 DLL into the executable's address space."""
    profile = DLL_LIFECYCLE_PROFILE if lifecycle else FIXED_DLL_PROFILE
    result, opt, table, flags = _inventory(data)
    for blocker in result['Blockers']:
        if blocker['Code'] not in ('PE-IMPORTS', 'PE-IAT'):
            raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    if abi != profile['AbiVersion'] or format_version != FORMAT_VERSION:
        raise Rejection('PE-DLL-PROFILE', 0, 'SBEF v2 ABI 1')
    if result['ImageBase'] != BASE - SEPARATE_ALIGNMENT or 'base_relocations' in result['Directories']:
        raise Rejection('PE-DLL-PROFILE', opt + 24, 'EXE.ImageBase')
    executable = _admit_separate(data, result, opt, table, flags)

    module, dll_opt, dll_table, dll_flags = _inventory(dll)
    for directory in module['Directories']:
        if directory not in ('exports', 'debug'):
            index = next((index for index, (name, _) in DIRECTORIES.items() if name == directory), None)
            if index is None:
                index = int(directory.removeprefix('directory_'))
            raise Rejection('PE-DLL-DIRECTORY', dll_opt + 112 + 8 * index, f'DLL.{directory}')
    if (module['ImageKind'] != 'DLL' or bool(module['EntryRVA']) != lifecycle or not dll_flags & 1
            or not 0x40800000 <= module['ImageBase'] < END or len(module['Sections']) > 5):
        raise Rejection('PE-DLL-PROFILE', dll_opt + 16, 'DLL.Characteristics/EntryPoint/ImageBase')
    if lifecycle and module['ImageBase'] != DLL_LIFECYCLE_BASE:
        raise Rejection('PE-DLL-PROFILE', dll_opt + 24, 'DLL.ImageBase')
    _validate_generic_debug(dll, module, dll_opt, dll_table, library=True)
    segments = _admit_relocated(dll, module, dll_opt, dll_table, dll_flags, (),
                                load_base=module['ImageBase'], library=True)
    name, exports = code_exports(module, segments, dll_opt, 2 if lifecycle else 1)
    if lifecycle and exports.get(DLL_ENTRY_EXPORT) != module['ImageBase'] + module['EntryRVA']:
        raise Rejection('PE-DLL-ENTRY', dll_opt + 16, 'DLL.AddressOfEntryPoint/BmoDllEntry')
    if lifecycle and len(set(exports.values())) != 2:
        raise Rejection('PE-DLL-ENTRY', dll_opt + 16, 'DLL.DuplicateExportAddress')
    bind_fixed_imports(data, result, opt, executable, name, exports, segments)
    package = _encode_pe_segments(executable + segments, abi, result['ImageBase'] + result['EntryRVA'],
                                  isa_profile, format_version)
    return package, dict(Name=name, Profile=profile['Name'], ImageBase=f'0x{module["ImageBase"]:X}',
                         Exports={symbol: f'0x{address:X}' for symbol, address in exports.items()})
