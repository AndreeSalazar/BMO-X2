"""Import static freestanding ELF64 on the host."""
import struct

from ..diagnostics import Rejection
from ..sbef.format import (BASE, END, FORMAT_VERSION, HEADER, MACHINE, MAX_IMAGE,
                           MAX_REGIONS, PAGE, PERMISSIONS, REGION, encode_header,
                           inspect, image_limit)

MAX_ELF = 16 * MAX_IMAGE
ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
ELF_PROGRAM = struct.Struct("<IIQQQQQQ")


def pack_elf(elf, *, abi=0, profile='default', isa_profile='x86-64-v1',
             format_version=FORMAT_VERSION):
    if not ELF_HEADER.size <= len(elf) <= MAX_ELF:
        raise Rejection('ELF-SIZE', min(len(elf), MAX_ELF), 'file')
    ident, kind, machine, version, entry, table, _, flags, header_size, ph_size, count, *_ = ELF_HEADER.unpack_from(elf)
    for value, expected, offset, field in [
            (ident[:7], b'\x7fELF\x02\x01\x01', 0, 'e_ident'),
            (kind, 2, 16, 'e_type'), (machine, MACHINE, 18, 'e_machine'),
            (version, 1, 20, 'e_version'), (flags, 0, 48, 'e_flags')]:
        if value != expected:
            raise Rejection('ELF-HEADER', offset, field)
    if (header_size != ELF_HEADER.size or ph_size != ELF_PROGRAM.size or not 1 <= count <= 32
            or table < header_size or table + count * ph_size > len(elf)):
        raise Rejection('ELF-PROGRAM-TABLE', 32, 'e_phoff/e_phentsize/e_phnum')

    segments = []
    for index in range(count):
        record = table + index * ph_size
        kind, perms, offset, address, _, filesz, memsz, align = ELF_PROGRAM.unpack_from(elf, record)
        if kind in (0, 6) or (kind == 0x6474e551 and not perms & 1):
            continue
        if kind != 1:
            code = {2: 'ELF-DYNAMIC', 3: 'ELF-INTERPRETER', 7: 'ELF-TLS'}.get(kind, 'ELF-UNSUPPORTED-SEGMENT')
            raise Rejection(code, record, 'p_type', index)
        if not memsz or filesz > memsz:
            raise Rejection('ELF-SEGMENT-SIZE', record + 40, 'p_memsz', index)
        if offset > len(elf) or filesz > len(elf) - offset:
            raise Rejection('ELF-SEGMENT-SIZE', record + 32, 'p_filesz', index)
        if perms not in PERMISSIONS:
            raise Rejection('ELF-PERMISSIONS', record + 4, 'p_flags', index)
        if address % PAGE or offset % PAGE or align != PAGE:
            raise Rejection('ELF-SEGMENT-LAYOUT', record + 48, 'p_align/p_vaddr/p_offset', index)
        if not BASE <= address < address + memsz <= END:
            raise Rejection('ELF-SEGMENT-ADDRESS', record + 16, 'p_vaddr', index)
        segments.append((address, offset, filesz, memsz, perms, index))
    if not 1 <= len(segments) <= MAX_REGIONS:
        raise Rejection('ELF-REGION-COUNT', 56, 'e_phnum')

    ordered = sorted(segments)
    previous_end = BASE
    for address, _, _, memsz, _, index in ordered:
        if address < previous_end:
            raise Rejection('ELF-SEGMENT-OVERLAP', table + index * ph_size + 16, 'p_vaddr', index)
        previous_end = address + ((memsz + PAGE - 1) // PAGE) * PAGE
    if not any(perms == 5 and address <= entry < address + filesz for address, _, filesz, _, perms, _ in ordered):
        raise Rejection('ELF-ENTRY', 24, 'e_entry')

    cursor = HEADER.size + len(segments) * REGION.size
    size = cursor + sum(segment[2] for segment in segments)
    if size > image_limit(profile):
        raise Rejection('ELF-OUTPUT-SIZE', 56, 'e_phnum')
    table = bytearray()
    payload = bytearray()
    for address, offset, filesz, memsz, perms, _ in ordered:
        table.extend(REGION.pack(address, cursor, filesz, memsz, perms, 0))
        payload.extend(elf[offset:offset+filesz])
        cursor += filesz
    header = encode_header(abi, len(segments), size, entry,
                           isa_profile=isa_profile, format_version=format_version)
    image = header + table + payload
    inspect(image, profile=profile)
    return image
