"""Inventory PE32+ headers on the host."""
import struct

from .diagnostics import Rejection


COFF = struct.Struct('<HHIIIHH')
SECTION = struct.Struct('<8sIIIIIIHHI')
DIRECTORIES = {
    1: ('imports', 'PE-IMPORTS'),
    3: ('exceptions', 'PE-EXCEPTIONS'),
    5: ('base_relocations', 'PE-RELOCATIONS'),
    9: ('tls', 'PE-TLS'),
    13: ('delay_imports', 'PE-DELAY-IMPORTS'),
    14: ('clr', 'PE-CLR'),
}


def probe_pe(data):
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
    for index, (name, code) in DIRECTORIES.items():
        if index >= directory_count:
            continue
        record = opt + 112 + index * 8
        rva, size = struct.unpack_from('<II', data, record)
        if rva or size:
            directories[name] = dict(RVA=rva, Bytes=size)
            blockers.append(Rejection(code, record, f'DataDirectory.{name}').report())
    if not blockers:
        blockers.append(Rejection('PE-IMPORTER-PENDING', opt + 68, 'Subsystem').report())
    return dict(SourceFormat='PE32+', Architecture='x86-64', EntryRVA=entry, ImageBase=base,
                Subsystem=subsystem, Sections=sections, Directories=directories,
                CanPack=False, Blockers=blockers)
