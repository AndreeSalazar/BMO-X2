"""HOST sequence tests executing the actual x86-64 per-port debounce helper."""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    build = ROOT / 'build/xhci-debounce-test'
    build.mkdir(exist_ok=True)
    source, obj, dll = (build / name for name in ('wrapper.S', 'wrapper.obj', 'validator.dll'))
    helper = ROOT / 'kernel/drivers/bus/xhci_debounce.inc'
    source.write_text('''
.text
.globl sample_ports
sample_ports:
    push %rsi
    sub $32, %rsp
    mov %rcx, %rsi
    mov %r8d, %ecx
    call xhci_debounce_sample
    add $32, %rsp
    pop %rsi
    ret
''' + f'#include "{helper.as_posix()}"\n', encoding='ascii')
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    subprocess.run([llvm / 'clang.exe', '--target=x86_64-pc-windows-msvc', '-c', source, '-o', obj], check=True)
    subprocess.run([llvm / 'lld-link.exe', '/dll', '/noentry', '/export:sample_ports', f'/out:{dll}', obj], check=True)
    library = ctypes.WinDLL(str(dll))
    sample = library.sample_ports
    sample.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32)
    sample.restype = ctypes.c_uint32
    results = []

    def sequence(name, snapshots, ready_at):
        ports = len(snapshots[0])
        counters = ctypes.create_string_buffer(ports)
        registers = ctypes.create_string_buffer(ports * 16)
        first_ready = None
        for tick, values in enumerate(snapshots, 1):
            for i, value in enumerate(values):
                struct.pack_into('<I', registers, i * 16, value)
            flags = sample(ctypes.addressof(counters), ctypes.addressof(registers), ports)
            if flags == 1 and first_ready is None:
                first_ready = tick
            assert all(value <= 11 for value in counters.raw), (name, counters.raw)
        assert first_ready == ready_at, (name, first_ready, ready_at)
        results.append(dict(name=name, first_ready_tick=first_ready, passed=True))

    sequence('steady', [[0x201]] * 11, 11)
    sequence('empty', [[0x200]] * 100, None)
    sequence('disconnect-restarts', [[0x201]] * 8 + [[0x200]] + [[0x201]] * 11, 20)
    sequence('change-flag-restarts', [[0x201]] * 8 + [[0x20201]] + [[0x201]] * 10, 19)
    sequence('persistent-change-never-ready', [[0x20201]] * 100, None)
    sequence('power-lost', [[0x201]] * 5 + [[1]] + [[0x201]] * 11, 17)
    sequence('second-port-arrives', [[0x201, 0x200]] * 5 + [[0x201, 0x201]] * 11, 16)
    sequence('empty-port-does-not-block', [[0x201, 0x200]] * 11, 11)
    sequence('unpowered-port-blocks', [[0x201, 0]] * 100, None)
    sequence('maximum-port-count', [[0x201] * 255] * 11, 11)
    report = dict(evidence='HOST', scope='Actual assembly helper, synthetic PORTSC snapshots; no USB emulation',
                  passed=len(results), total=len(results), cases=results)
    (build / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
