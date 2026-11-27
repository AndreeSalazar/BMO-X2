"""Compare a successful OpenRM GSP_INIT with the assembled BMO-X2 request."""

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zlib


HEADER = struct.Struct('<6I2IQI5I')
MCTP_MAGIC = b'PTCM'
CAPTURE_LINE = re.compile(r'BMO_GSP_INIT_(OK_BEGIN|WORD|OK_END)=([^\r\n]+)')
DMA_KEYS = {0x1021, 0x1022}
RUNTIME_KEYS = {0x0003, 0x0052, 0x1000, 0x1031}
TX_RECEIPT = re.compile(r'INIT TX / REV ([0-9a-f]{8}) LINK ([0-9a-f]{8}) '
                        r'PCIE ([0-9a-f]{8}) MEM ([0-9a-f]{8})(?: CL ([0-9a-f]{8}))? CRC ([0-9a-f]{8})', re.I)


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


def read_bmo_frame(image):
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
        matches.append(image[offset:offset+total])
    if len(matches) != 1:
        raise ValueError('Expected one assembled BMO-X2 GSP_INIT frame')
    return matches[0]


def read_bmo(image, tx_receipt=None):
    frame = read_bmo_frame(image)
    if tx_receipt is None:
        return frame[HEADER.size:]

    match = TX_RECEIPT.fullmatch(tx_receipt.strip())
    if not match:
        raise ValueError('Expected the complete INIT TX line from BMO-X2')
    rev_text, link_text, pcie_text, mem_text, core_logic, crc_text = match.groups()
    revision, link, pcie, console, expected_crc = (
        int(word, 16) for word in (rev_text, link_text, pcie_text, mem_text, crc_text))
    if len(frame) != (544 if core_logic is not None else 528):
        raise ValueError('INIT receipt and EFI template use different frame versions')
    if core_logic is not None and struct.unpack_from('<2IQ', frame, 528) != (0x20001033, 1, int(core_logic, 16)):
        raise ValueError('INIT TX CL value differs from the EFI template')
    frame = bytearray(frame)
    for offset, key, fmt, value in ((80, 3, '<I', revision), (256, 0x52, '<I', link),
                                    (328, 0x20001000, '<Q', pcie), (184, 0x20001031, '<Q', console)):
        value_offset = offset + (4 if fmt == '<I' else 8)
        if value_offset + struct.calcsize(fmt) > len(frame) or struct.unpack_from('<I', frame, offset)[0] != key:
            raise ValueError('INIT template does not match the captured layout')
        struct.pack_into(fmt, frame, value_offset, value)
    if zlib.crc32(frame) != expected_crc:
        raise ValueError('INIT TX checksum differs. Check the copied receipt and use the EFI from that boot')
    return bytes(frame[HEADER.size:])


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


def compare(reference, bmo, *, runtime_verified=False):
    differences = []
    for key, index in sorted(reference.keys() | bmo.keys()):
        slot = key, index
        left, right = reference.get(slot), bmo.get(slot)
        sampled = key in RUNTIME_KEYS and not runtime_verified
        if left == right and not sampled:
            continue
        if sampled and right is not None:
            kind = 'sampled_in_bmo_at_boot'
        elif left is None or right is None:
            kind = 'missing_from_openrm' if left is None else 'missing_from_bmo'
        elif key in DMA_KEYS:
            kind = 'dma_address_requires_role_comparison'
        else:
            kind = 'different_value'
        differences.append(dict(key=f'0x{key:04X}', index=index, kind=kind,
                                openrm=left, **{'bmo_tx' if runtime_verified else 'bmo_template': right}))
    return differences


def validate_with_gcc(gcc, payloads):
    """Run the freestanding C validator in a Windows HOST DLL."""
    if os.name != 'nt':
        raise ValueError('--gcc requires Windows x64 HOST and LLVM')
    from _ctypes import FreeLibrary

    llvm = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'
    source = Path(__file__).with_name('gsp_init_nvkv.c').resolve()
    with tempfile.TemporaryDirectory(prefix='bmo-gsp-init-') as temp:
        work = Path(temp)
        subprocess.run([gcc.resolve(), '-std=c11', '-O2', '-ffreestanding',
                        '-fno-stack-protector', '-fno-asynchronous-unwind-tables',
                        '-fno-jump-tables', '-Wall', '-Wextra', '-Werror',
                        '-c', source, '-o', 'nvkv.o'], cwd=work, check=True)
        relocations = subprocess.check_output(
            [llvm/'llvm-readobj.exe', '--relocations', 'nvkv.o'], cwd=work, text=True)
        if not re.search(r'Relocations \[\s*\]', relocations):
            raise ValueError('Freestanding NVKV object contains relocations')
        subprocess.run([llvm/'llvm-objcopy.exe', '-O', 'binary',
                        '--only-section=.text.gsp_nvkv', 'nvkv.o', 'nvkv.bin'],
                       cwd=work, check=True)
        (work/'entry.S').write_text('.text\n.globl gsp_validate_nvkv\n'
                                   'gsp_validate_nvkv:\n.incbin "nvkv.bin"\n',
                                   encoding='ascii')
        subprocess.run([llvm/'clang.exe', '--target=x86_64-pc-windows-msvc',
                        '-c', 'entry.S', '-o', 'entry.obj'], cwd=work, check=True)
        subprocess.run([llvm/'lld-link.exe', '/dll', '/noentry', '/nodefaultlib',
                        '/export:gsp_validate_nvkv', '/out:nvkv.dll', 'entry.obj'],
                       cwd=work, check=True)
        library = ctypes.WinDLL(str(work/'nvkv.dll'))
        try:
            validate = library.gsp_validate_nvkv
            validate.argtypes = (ctypes.c_char_p, ctypes.c_size_t)
            validate.restype = ctypes.c_size_t
            for name, payload in payloads.items():
                failure = validate(payload, len(payload))
                if failure:
                    raise ValueError(f'{name}: C validator rejected NVKV at byte {failure-1:#x}')
        finally:
            FreeLibrary(library._handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('openrm_log', type=Path)
    parser.add_argument('bmo_image', type=Path, help='Assembled amdvi-firmware.bin or RTX-FWSEC.EFI')
    parser.add_argument('--gcc', type=Path, help='x86-64 ELF GCC for independent C validation on HOST')
    parser.add_argument('--tx', help='Complete INIT TX line from the physical desktop or serial log')
    args = parser.parse_args()
    try:
        payloads = {'OpenRM': read_openrm(args.openrm_log.read_text(encoding='utf-8-sig')),
                    'BMO-X2': read_bmo(args.bmo_image.read_bytes(), args.tx)}
        if args.gcc:
            validate_with_gcc(args.gcc, payloads)
        reference = decode_nvkv(payloads['OpenRM'])
        bmo = decode_nvkv(payloads['BMO-X2'])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'GSP_INIT: {error}\n')
    report = dict(openrm_keys=len(reference), bmo_keys=len(bmo),
                  differences=compare(reference, bmo, runtime_verified=args.tx is not None))
    if args.tx is not None:
        report['bmo_tx_crc_verified'] = True
    if args.gcc:
        report['gcc_nvkv_checked_bytes'] = {name: len(payload) for name, payload in payloads.items()}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
