"""Compare a successful OpenRM GSP_INIT with the assembled BMO-X2 request."""

import argparse
import json
from pathlib import Path
import re
import struct


HEADER = struct.Struct('<6I2IQI5I')
MCTP_MAGIC = b'PTCM'
CAPTURE_LINE = re.compile(r'BMO_GSP_INIT_(OK_BEGIN|WORD|OK_END)=([^\r\n]+)')
DMA_KEYS = {0x1021, 0x1022}
RUNTIME_KEYS = {0x0003, 0x0052}


def read_openrm(log):
    words = []
    expected = None
    for kind, value in CAPTURE_LINE.findall(log):
        if kind == 'OK_BEGIN':
            expected = int(value, 10)
            words = []
            if not 0 < expected <= 8192:
                raise ValueError('OpenRM capture word count is invalid')
        elif kind == 'WORD' and expected is not None:
            index, word = value.split()
            if len(word) != 16 or int(index, 16) != len(words) or len(words) >= expected:
                raise ValueError('OpenRM capture has an invalid or missing word')
            words.append(int(word, 16))
        elif kind == 'OK_END' and expected is not None:
            if len(words) != expected or int(value, 10) != expected:
                raise ValueError('OpenRM capture is incomplete')
            return struct.pack(f'<{expected}Q', *words)
    raise ValueError('No complete successful OpenRM capture found')


def read_bmo(image):
    matches = []
    for match in re.finditer(MCTP_MAGIC, image):
        offset = match.start()
        if offset + HEADER.size > len(image):
            continue
        magic, total, transport, vendor, inner, reserved, command, size, seq, capacity, *tail = (
            HEADER.unpack_from(image, offset)
        )
        if (magic, transport, vendor, reserved, command, seq, capacity) != (
                0x4D435450, 0xC0000001, 0x2610DE7E, 0, 0x10001, 1, 48*1024):
            continue
        if (any(tail) or not 0 < size <= 4096-HEADER.size or size % 8
                or total != HEADER.size + size or inner != total-24
                or offset + total > len(image)):
            raise ValueError('Malformed BMO-X2 GSP_INIT frame')
        matches.append(image[offset+HEADER.size:offset+total])
    if len(matches) != 1:
        raise ValueError('Expected one assembled BMO-X2 GSP_INIT frame')
    return matches[0]


def decode_nvkv(payload):
    if len(payload) % 8:
        raise ValueError('NVKV payload must be aligned to 8 bytes')
    values = {}
    offset = 0
    while offset < len(payload):
        tag, count = struct.unpack_from('<II', payload, offset)
        offset += 8
        opcode, index, key = tag >> 28, (tag >> 16) & 0xfff, tag & 0xffff
        if opcode == 0:
            value = ('u32', count)
            values.setdefault((key, index), []).append(value)
            continue
        if opcode > 5 or not count:
            raise ValueError(f'Unknown or empty NVKV instruction at {offset-8:#x}')
        fmt, width = {1: ('I', 4), 2: ('Q', 8), 3: ('B', 1),
                      4: ('I', 4), 5: ('Q', 8)}[opcode]
        end = offset + ((width*count+7) & -8)
        if end > len(payload):
            raise ValueError('Truncated NVKV instruction')
        data = struct.unpack_from(f'<{count}{fmt}', payload, offset)
        offset = end
        if opcode in (1, 2):
            if key + count > 0x10000:
                raise ValueError('NVKV sequence overflows its key range')
            for step, item in enumerate(data):
                values.setdefault((key+step, index), []).append((f'u{width*8}', item))
        else:
            values.setdefault((key, index), []).append((f'array{width*8}', data))
    return values


def compare(reference, bmo):
    differences = []
    for key, index in sorted(reference.keys() | bmo.keys()):
        slot = key, index
        left, right = reference.get(slot), bmo.get(slot)
        if left == right and key not in RUNTIME_KEYS:
            continue
        if key in RUNTIME_KEYS and right is not None:
            kind = 'sampled_in_bmo_at_boot'
        elif left is None or right is None:
            kind = 'missing_from_openrm' if left is None else 'missing_from_bmo'
        elif key in DMA_KEYS:
            kind = 'dma_address_requires_role_comparison'
        else:
            kind = 'different_value'
        differences.append(dict(key=f'0x{key:04X}', index=index, kind=kind,
                                openrm=left, bmo_template=right))
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('openrm_log', type=Path)
    parser.add_argument('bmo_image', type=Path, help='Assembled amdvi-firmware.bin or RTX-FWSEC.EFI')
    args = parser.parse_args()
    try:
        reference = decode_nvkv(read_openrm(args.openrm_log.read_text(encoding='utf-8-sig')))
        bmo = decode_nvkv(read_bmo(args.bmo_image.read_bytes()))
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP_INIT: {error}\n')
    print(json.dumps(dict(openrm_keys=len(reference), bmo_keys=len(bmo),
                          differences=compare(reference, bmo)), indent=2))


if __name__ == '__main__':
    main()
