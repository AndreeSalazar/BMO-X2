"""Check the physical shutdown guards and its TSC poll without device I/O."""

import ctypes as c
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[3]
LLVM = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'

SOURCE = r"""
#define BMO_STORAGE_STATE
#define BMO_STORAGE_QUIESCE
#define BMO_STORAGE_QUIESCE_METAL
#include "kernel/drivers/bus/amdvi/post_layout.inc"
.text
.globl guard_fixture
guard_fixture:
    push %rbp
    push %rsi
    push %rdi
    push %r12
    push %r13
    mov %rcx, %rbp
    lea STORAGE_ROWS(%rbp), %r12
    xor %r13d, %r13d
    call storage_quiesce
    pop %r13
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbp
    ret
.globl wait_fixture
wait_fixture:
    push %rbp
    push %rdi
    mov %rcx, %rbp
    mov %rdx, %rdi
    mov $1, %r10d
    call .Lquiesce_wait
    setc %al
    movzbl %al, %eax
    pop %rdi
    pop %rbp
    ret
.globl calibrate_fixture
calibrate_fixture:
    push %rbp
    sub $32, %rsp
    mov %rdx, %rbp
    call storage_calibrate_tsc
    add $32, %rsp
    pop %rbp
    ret
#include "kernel/drivers/storage/quiesce.inc"
#include "kernel/drivers/storage/calibrate_tsc.inc"
"""


@unittest.skipUnless(os.name == 'nt', 'requires Windows and LLVM')
class PhysicalStorageQuiesce(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix='bmo-storage-quiesce-')
        cls.addClassCleanup(folder.cleanup)
        source = Path(folder.name) / 'shutdown.S'
        obj, dll = source.with_suffix('.obj'), source.with_suffix('.dll')
        source.write_text(SOURCE, encoding='ascii')
        subprocess.run([LLVM / 'clang.exe', '--target=x86_64-pc-windows-msvc', '-I', ROOT,
                        '-c', source, '-o', obj], check=True)
        subprocess.run([LLVM / 'lld-link.exe', '/dll', '/noentry', '/nodefaultlib', '/export:guard_fixture',
                        '/export:wait_fixture', '/export:calibrate_fixture', f'/out:{dll}', obj], check=True)
        library = c.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, library._handle)
        cls.guard = library.guard_fixture
        cls.guard.argtypes = [c.c_void_p]
        cls.guard.restype = None
        cls.poll = library.wait_fixture
        cls.poll.argtypes = [c.c_void_p, c.c_void_p, c.c_uint32, c.c_uint32]
        cls.poll.restype = c.c_uint32
        cls.calibrate = library.calibrate_fixture
        cls.calibrate.argtypes = [c.c_void_p, c.c_void_p]
        cls.calibrate.restype = None

    @staticmethod
    def context():
        context = c.create_string_buffer(4096)
        struct.pack_into('<I', context, 0x814, 7)
        struct.pack_into('<QIIQQ', context, 0xb00, 0xfd500000, 0x80000244, 0xfd500001, 4, 0x220000000400)
        struct.pack_into('<II', context, 0xb50, 2, 2)
        struct.pack_into('<Q', context, 0xb78, 1000000)
        struct.pack_into('<HHIQQIHH', context, 0xf90, 0x0301, 6, 0x010601, 0xfc000000, 4096, 0x43b81022, 6, 2)
        return context

    def test_platform_mismatch_cannot_reach_the_mmio_write_path(self):
        for offset, size, value in (
            (0xb00, 'Q', 0xfed80000), (0xb08, 'I', 0x80000344), (0xb10, 'Q', 1),
            (0xb18, 'Q', 0x1005), (0xb78, 'Q', 0), (0x814, 'I', 6), (0xb54, 'I', 3),
            (0xf90, 'H', 0x0302), (0xfa8, 'I', 0x29228086), (0xfac, 'H', 2),
        ):
            with self.subTest(offset=offset):
                context = self.context()
                struct.pack_into('<' + size, context, offset, value)
                self.guard(context)
                self.assertEqual(context.raw[0xb58:0xb78], bytes(32))

    def test_pending_tsc_poll_ends_and_invalid_mmio_fails(self):
        context = self.context()
        for observed, wanted, failure in ((8,8,0), (0,8,1), (0xffffffff,0,1)):
            with self.subTest(observed=observed):
                self.assertEqual(self.poll(context, c.byref(c.c_uint32(observed)), 0x4e, wanted), failure)

    def test_uefi_stall_calibration(self):
        calls = []

        def stall(microseconds):
            calls.append(microseconds)
            deadline = time.perf_counter_ns() + microseconds*1000
            while time.perf_counter_ns() < deadline:
                pass
            return 0

        callback = c.WINFUNCTYPE(c.c_int64, c.c_uint64)(stall)
        services = (c.c_void_p*32)()
        services[0xf8//8] = c.cast(callback, c.c_void_p).value
        context = c.create_string_buffer(4096)
        self.calibrate(services, context)
        if not calls:
            self.skipTest('CPU did not advertise invariant TSC')
        interval, = struct.unpack_from('<Q', context, 0xb78)
        self.assertEqual(calls, [10000])
        self.assertTrue(1000000 <= interval <= 100000000)


if __name__ == '__main__':
    unittest.main()
