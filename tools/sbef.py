"""Pack a freestanding ELF64 image into the provisional SBEF format."""
import argparse
import json
from pathlib import Path
import struct
import tempfile


PAGE = 4096
BASE = 0x40000000
END = BASE + 16 * 1024 * 1024
MAX_IMAGE = 1024 * 1024
MAX_ELF = 16 * MAX_IMAGE
MAX_REGIONS = 8
MACHINE = 62
HEADER = struct.Struct('<4sHHHHIQII')
REGION = struct.Struct('<QIIIIQ')
ELF_HEADER = struct.Struct('<16sHHIQQQIHHHHHH')
ELF_PROGRAM = struct.Struct('<IIQQQQQQ')
PERMISSIONS = {4: 'R', 5: 'RX', 6: 'RW'}


def inspect(image):
    if not HEADER.size <= len(image) <= MAX_IMAGE:
        raise ValueError('SBEF-SIZE')
    magic, version, abi, machine, count, size, entry, flags, reserved = HEADER.unpack_from(image)
    if (magic, version, abi, machine, flags, reserved) != (b'SBEF', 1, 0, MACHINE, 0, 0):
        raise ValueError('SBEF-HEADER')
    cursor = HEADER.size + count * REGION.size
    if not 1 <= count <= MAX_REGIONS or not cursor <= size == len(image):
        raise ValueError('SBEF-TABLE')

    previous_end = BASE
    entry_in_text = False
    regions = []
    for index in range(count):
        address, offset, filesz, memsz, perms, reserved = REGION.unpack_from(image, HEADER.size + index * REGION.size)
        if reserved or perms not in PERMISSIONS or not 0 <= filesz <= memsz or not memsz:
            raise ValueError('SBEF-REGION')
        end = address + ((memsz + PAGE - 1) // PAGE) * PAGE
        if address % PAGE or not previous_end <= address < end <= END:
            raise ValueError('SBEF-VIRTUAL-RANGE')
        if offset != cursor or filesz > size - cursor:
            raise ValueError('SBEF-FILE-RANGE')
        cursor += filesz
        previous_end = end
        entry_in_text |= perms == 5 and address <= entry < address + filesz
        regions.append(dict(Address=f'0x{address:X}', Offset=offset, FileBytes=filesz, MemoryBytes=memsz,
                            MappedBytes=end-address, Permissions=PERMISSIONS[perms]))
    if cursor != size or not entry_in_text:
        raise ValueError('SBEF-PAYLOAD-OR-ENTRY')
    return dict(FormatVersion=version, AbiVersion=abi, Architecture='x86-64', Bytes=size,
                Entry=f'0x{entry:X}', Regions=regions)


def pack_elf(elf):
    if not ELF_HEADER.size <= len(elf) <= MAX_ELF:
        raise ValueError('ELF-SIZE')
    ident, kind, machine, version, entry, table, _, flags, header_size, ph_size, count, *_ = ELF_HEADER.unpack_from(elf)
    if (ident[:7], kind, machine, version, flags) != (b'\x7fELF\x02\x01\x01', 2, MACHINE, 1, 0):
        raise ValueError('ELF-HEADER')
    if (header_size != ELF_HEADER.size or ph_size != ELF_PROGRAM.size or not 1 <= count <= 32
            or table < header_size or table + count * ph_size > len(elf)):
        raise ValueError('ELF-PROGRAM-TABLE')

    segments = []
    for index in range(count):
        kind, perms, offset, address, _, filesz, memsz, align = ELF_PROGRAM.unpack_from(elf, table + index * ph_size)
        if kind in (0, 6) or (kind == 0x6474e551 and not perms & 1):
            continue
        if kind != 1:
            raise ValueError(f'ELF-UNSUPPORTED-SEGMENT-{kind:#x}')
        if not memsz or filesz > memsz or offset > len(elf) or filesz > len(elf) - offset:
            raise ValueError('ELF-SEGMENT-SIZE')
        if perms not in PERMISSIONS or address % PAGE or offset % PAGE or align != PAGE:
            raise ValueError('ELF-SEGMENT-LAYOUT')
        if not BASE <= address < address + memsz <= END:
            raise ValueError('ELF-SEGMENT-ADDRESS')
        segments.append((address, offset, filesz, memsz, perms))
    if not 1 <= len(segments) <= MAX_REGIONS:
        raise ValueError('ELF-REGION-COUNT')

    cursor = HEADER.size + len(segments) * REGION.size
    size = cursor + sum(segment[2] for segment in segments)
    if size > MAX_IMAGE:
        raise ValueError('SBEF-SIZE')
    table = bytearray()
    payload = bytearray()
    for address, offset, filesz, memsz, perms in sorted(segments):
        table.extend(REGION.pack(address, cursor, filesz, memsz, perms, 0))
        payload.extend(elf[offset:offset+filesz])
        cursor += filesz
    image = HEADER.pack(b'SBEF', 1, 0, MACHINE, len(segments), size, entry, 0, 0) + table + payload
    inspect(image)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    pack = commands.add_parser('pack')
    pack.add_argument('input', type=Path)
    pack.add_argument('output', type=Path)
    commands.add_parser('inspect').add_argument('input', type=Path)
    args = parser.parse_args()
    with args.input.open('rb') as file:
        data = file.read((MAX_ELF if args.action == 'pack' else MAX_IMAGE) + 1)
    if args.action == 'pack':
        if args.output.resolve() == args.input.resolve():
            raise ValueError('SBEF-OUTPUT-ALIAS')
        data = pack_elf(data)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as file:
                temp = Path(file.name)
                file.write(data)
            temp.replace(args.output)
        finally:
            if temp:
                temp.unlink(missing_ok=True)
    print(json.dumps(inspect(data), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f'RED [{error}]') from error
