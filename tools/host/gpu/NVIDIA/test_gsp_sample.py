"""Exercise the real GSP probe with a mocked EFI PCI I/O protocol on Windows."""

import ctypes as c
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'
OFFSETS = (0, 0x111388, 0x110040, 0x840040, 0x118128, 0x118234, 0x1183a4,
           0x625f04, 0x1fa7c8, 0x1fa82c, 0x1fa830, 0x1fa828)
REGISTERS = (0xb76000a1, 0x00000010, 0xbadf1002, 0x00000015, 1, 0xff, 0x3000,
             0x02fff008, 1, 0x10, 0, 0)
EMPTY = b'GSP1=--------,--------,--------'
EMPTY_WPR = b'WPR='+b','.join([b'--------']*8)
COMPLETE_WPR = b'WPR='+b','.join(f'{value:08X}'.encode('ascii') for value in REGISTERS[4:])

FIXTURE = r"""
.text
.globl probe_fixture
probe_fixture:
    push %rbp
    push %r12
    push %r13
    push %r14
    push %rsi
    push %rdi
    sub $40, %rsp
    mov %rcx, %r14
    mov %rdx, %rbp
    mov $0x80290000, %r12d
    mov $0xfb000000, %r13d
    lea report_template(%rip), %rsi
    lea 0xc00(%rbp), %rdi
    mov $(report_end-report_template), %ecx
    cld
    rep movsb
    call nvidia_mmio_probe
    add $40, %rsp
    pop %rdi
    pop %rsi
    pop %r14
    pop %r13
    pop %r12
    pop %rbp
    ret
#include "kernel/boot/bridge/desktop_boot_report.inc"
"""


class PciIo:
    def __init__(self, *, pci_id=0x250410de, aperture=0x1000000, command=3,
                 denied=None, changed=False):
        self.boot = (c.c_void_p * (0x140 // 8))()
        self.protocol = (c.c_void_p * (0x88 // 8))()
        self.resource = c.create_string_buffer(46)
        struct.pack_into('<BHB', self.resource, 0, 0x8a, 43, 0)
        struct.pack_into('<Q', self.resource, 14, 0xfb000000)
        struct.pack_into('<Q', self.resource, 38, aperture)
        self.handles = (c.c_uint64 * 1)(0x42)
        self.callbacks = []
        self.reads = []
        self.freed = []
        self.command_reads = 0

        def bind(table, offset, argc, fn):
            callback = c.WINFUNCTYPE(c.c_int64, *([c.c_uint64] * argc))(fn)
            self.callbacks.append(callback)
            table[offset // 8] = c.cast(callback, c.c_void_p).value

        def put(ptr, typ, value):
            typ.from_address(ptr).value = value

        def locate(_search, _guid, _key, count, buffer):
            put(count, c.c_uint64, 1)
            put(buffer, c.c_uint64, c.addressof(self.handles))
            return 0

        def handle(_handle, _guid, protocol):
            put(protocol, c.c_uint64, c.addressof(self.protocol))
            return 0

        def get_location(_self, segment, bus, device, function):
            for ptr, value in zip((segment, bus, device, function), (0, 0x29, 0, 0)):
                put(ptr, c.c_uint64, value)
            return 0

        def get_bar(_self, _bar, _supports, resource):
            put(resource, c.c_uint64, c.addressof(self.resource))
            return 0

        def read_config(_self, width, offset, count, result):
            if (width, offset, count) == (2, 0, 2):
                struct.pack_into('<II', (c.c_ubyte * 8).from_address(result), 0, pci_id, command)
                return 0
            if (width, offset, count) != (1, 4, 1):
                return -1
            self.command_reads += 1
            put(result, c.c_uint16, command | (4 if changed and self.command_reads == 2 else 0))
            return 0

        def read_mmio(_self, width, bar, offset, count, result):
            self.reads.append((width, bar, offset, count))
            if (width, bar, count) != (2, 0, 1) or offset not in OFFSETS or offset == denied:
                return -1
            put(result, c.c_uint32, REGISTERS[OFFSETS.index(offset)])
            return 0

        def free(ptr):
            self.freed.append(ptr)
            return 0

        bind(self.boot, 0x138, 5, locate)
        bind(self.boot, 0x98, 3, handle)
        bind(self.boot, 0x48, 1, free)
        bind(self.protocol, 0x70, 5, get_location)
        bind(self.protocol, 0x80, 4, get_bar)
        bind(self.protocol, 0x30, 5, read_config)
        bind(self.protocol, 0x10, 6, read_mmio)


@unittest.skipUnless(os.name == 'nt', 'requires Windows and LLVM')
class NvidiaGspSample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix='bmo-gsp-')
        cls.addClassCleanup(folder.cleanup)
        directory = Path(folder.name)
        source, obj, dll = directory / 'probe.S', directory / 'probe.obj', directory / 'probe.dll'
        source.write_text(FIXTURE, encoding='ascii')
        subprocess.run([LLVM / 'clang.exe', '--target=x86_64-pc-windows-msvc',
                        '-DBMO_NVIDIA_GSP_SAMPLE', '-DBMO_NVIDIA_PCI_PROBE', '-DRMLUI_MEDIA',
                        '-DBMO_NVIDIA_GSP_BOOT_CHAIN', '-DBMO_NVIDIA_GSP_STAGE',
                        '-DBMO_GSP_FILE_BYTES=27043992', '-DBMO_GSP_FILE_CRC=0',
                        '-I', ROOT, '-c', source, '-o', obj], check=True)
        subprocess.run([LLVM / 'lld-link.exe', '/dll', '/noentry', '/nodefaultlib',
                        '/export:probe_fixture', f'/out:{dll}', obj], check=True)
        cls.library = c.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, cls.library._handle)
        cls.probe = cls.library.probe_fixture
        cls.probe.argtypes = [c.c_void_p, c.c_void_p]
        cls.probe.restype = None

    def check_sample(self, offsets, status, expected=EMPTY, wpr=EMPTY_WPR, **settings):
        pci = PciIo(**settings)
        context = c.create_string_buffer(0x1000)
        self.probe(pci.boot, context)
        lines = context.raw[0xc00:].split(b'\0', 1)[0].splitlines()
        self.assertIn(f'GPU_MMIO_STATUS={status:08X}'.encode('ascii'), lines)
        self.assertIn(expected, lines)
        self.assertIn(wpr, lines)
        handoff = REGISTERS[4:] if wpr==COMPLETE_WPR else (0,)*8
        self.assertEqual(struct.unpack_from('<8I',context,0x8d0),handoff)
        self.assertEqual(pci.reads, [(2, 0, offset, 1) for offset in offsets])
        self.assertEqual(pci.freed, [c.addressof(pci.resource), c.addressof(pci.handles)])

    def test_reads_ga106(self):
        self.check_sample(OFFSETS, 8, b'GSP1=00000010,BADF1002,00000015', wpr=COMPLETE_WPR)

    def test_skips_other_vendor_or_active_dma(self):
        self.check_sample((), 3, pci_id=0x11111234)
        self.check_sample((), 4, command=7)

    def test_rejects_truncated_aperture(self):
        self.check_sample((0,), 8, aperture=0x840043)

    def test_discards_partial_snapshot(self):
        self.check_sample(OFFSETS[:3], 8, denied=0x110040)
        self.check_sample(OFFSETS[:7], 8, b'GSP1=00000010,BADF1002,00000015', denied=0x1183a4)

    def test_rechecks_command_after_sample(self):
        self.check_sample(OFFSETS, 7, changed=True)


if __name__ == '__main__':
    unittest.main()
