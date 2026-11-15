"""Execute the actual x86-64 layout validator with compact and invalid banks.

HOST only: no PCI, MMIO or controller emulation. QEMU covers the full probe.
"""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    build = ROOT / 'build/xhci-layout-test'
    build.mkdir(exist_ok=True)
    source = build / 'wrapper.S'
    validator = ROOT / 'kernel/drivers/bus/xhci_transport_layout.inc'
    source.write_text('''
.text
.globl validate_layout
validate_layout:
    push %rdi
    sub $32, %rsp
    mov %rcx, %rdi
    mov %edx, %r9d
    mov %r8d, %r10d
    call xhci_transport_layout
    setz %al
    movzbl %al, %eax
    add $32, %rsp
    pop %rdi
    ret
''' + f'#include "{validator.as_posix()}"\n', encoding='ascii')
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    obj, dll = build / 'wrapper.obj', build / 'validator.dll'
    subprocess.run([llvm / 'clang.exe', '--target=x86_64-pc-windows-msvc',
                    '-c', source, '-o', obj], check=True)
    subprocess.run([llvm / 'lld-link.exe', '/dll', '/noentry',
                    '/export:validate_layout', f'/out:{dll}', obj], check=True)
    library = ctypes.WinDLL(str(dll))
    validate = library.validate_layout
    validate.argtypes = (ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32)
    validate.restype = ctypes.c_uint32
    cases = [
        ('qemu', 8, 0x1000, 0x2000, True),
        ('compact-runtime-4c0', 4, 0x4c0, 0x460, True),
        ('compact-runtime-eight-ports', 8, 0x4c0, 0x1000, True),
        ('compact-doorbell-after-runtime', 4, 0x4c0, 0x500, True),
        ('same-extra-page', 8, 0x1000, 0x1040, True),
        ('last-runtime-in-page', 4, 0xfc0, 0x1000, True),
        ('runtime-port-overlap', 4, 0x440, 0x500, False),
        ('doorbell-port-overlap', 4, 0x4c0, 0x440, False),
        ('runtime-misaligned', 4, 0x4c4, 0x500, False),
        ('doorbell-misaligned', 4, 0x4c0, 0x502, False),
        ('runtime-crosses-page', 4, 0xfe0, 0x2000, False),
        ('bank-overlap', 4, 0x4c0, 0x4e0, False),
        ('same-bank', 4, 0x4c0, 0x4c0, False),
        ('runtime-outside-aperture', 4, 0x10000, 0x500, False),
        ('doorbell-outside-aperture', 4, 0x4c0, 0x10000, False),
    ]
    results = []
    for name, ports, runtime, doorbell, expected in cases:
        caps = ctypes.create_string_buffer(32)
        struct.pack_into('<II', caps, 0, 0x01000020, ports << 24 | 1)
        actual = bool(validate(ctypes.addressof(caps), runtime, doorbell))
        assert actual == expected, (name, actual, expected)
        results.append(dict(name=name, admitted=actual, passed=True))
    report = dict(evidence='HOST', scope='Actual assembly geometry validator; no hardware access',
                  cases=results, passed=len(results), total=len(cases))
    (build / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
