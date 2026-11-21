"""Compare the optional x86-64 encoder against the independent HOST encoder."""

import ctypes as c
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from .radix3 import DMA_LIMIT, ENTRIES, PAGE, encode


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'


FIXTURE = r"""
.text
.globl radix3_fixture
radix3_fixture:
    mov 40(%rsp), %r10
    push %rdi
    push %rsi
    sub $8, %rsp
    mov %rcx, %rdi
    mov %rdx, %rsi
    mov %r8, %rdx
    mov %r9, %rcx
    mov %r10, %r8
    call nvidia_gsp_radix3
    add $8, %rsp
    pop %rsi
    pop %rdi
    ret
#include "kernel/drivers/GPU/NVIDIA/gsp_radix3.inc"
"""


@unittest.skipUnless(os.name == 'nt', 'requires Windows and LLVM')
class NvidiaRadix3Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix='bmo-gsp-radix3-')
        cls.addClassCleanup(folder.cleanup)
        directory = Path(folder.name)
        source, obj, dll = directory/'probe.S', directory/'probe.obj', directory/'probe.dll'
        source.write_text(FIXTURE, encoding='ascii')
        subprocess.run([LLVM/'clang.exe', '--target=x86_64-pc-windows-msvc',
                        '-I', ROOT, '-c', source, '-o', obj], check=True)
        subprocess.run([LLVM/'lld-link.exe', '/dll', '/noentry', '/nodefaultlib',
                        '/export:radix3_fixture', f'/out:{dll}', obj], check=True)
        library = c.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, library._handle)
        cls.build = library.radix3_fixture
        cls.build.argtypes = [c.c_void_p] + [c.c_uint64]*4
        cls.build.restype = c.c_uint64

    def setUp(self):
        self.size = (ENTRIES+3)*PAGE
        self.memory = c.create_string_buffer(self.size+PAGE)
        self.base = (c.addressof(self.memory)+PAGE-1) & -PAGE
        c.memset(self.base, 0x5a, self.size)

    def test_matches_reference_and_preserves_the_next_byte(self):
        cases = (
            (1, PAGE, 2*PAGE),
            (512, 0x10000000, 0x40000000),
            (513, 0x40000000, 0x10000000),
            (6590, 0x08000000, 0x08000000+6591*PAGE),
            (262144, DMA_LIMIT-262144*PAGE, PAGE),
            (1, PAGE, DMA_LIMIT-3*PAGE),
        )
        for pages, image, directory in cases:
            with self.subTest(pages=pages, image=image, directory=directory):
                c.memset(self.base, 0x5a, self.size)
                directory_pages = (pages+ENTRIES-1)//ENTRIES+2
                root, data = encode(range(image, image+pages*PAGE, PAGE),
                                    range(directory, directory+directory_pages*PAGE, PAGE))
                self.assertEqual(self.build(self.base, image, directory, pages, len(data)), root)
                self.assertEqual(c.string_at(self.base, len(data)), data)
                self.assertEqual(c.string_at(self.base+len(data), 1), b'Z')

    def test_rejects_invalid_geometry_before_writing(self):
        cases = (
            (0, PAGE, 4*PAGE, 1, 3*PAGE),
            (self.base+1, PAGE, 4*PAGE, 1, 3*PAGE),
            (self.base, 0, 4*PAGE, 1, 3*PAGE),
            (self.base, PAGE+1, 4*PAGE, 1, 3*PAGE),
            (self.base, PAGE, 4*PAGE+1, 1, 3*PAGE),
            (self.base, PAGE, 4*PAGE, 1, 3*PAGE-1),
            (self.base, PAGE, 4*PAGE, 0, 3*PAGE),
            (self.base, PAGE, 4*PAGE, 262145, self.size),
            (self.base, PAGE, 2*PAGE, 2, 3*PAGE),
            (self.base, 3*PAGE, PAGE, 1, 3*PAGE),
            (self.base, DMA_LIMIT-PAGE, PAGE, 2, 3*PAGE),
            (self.base, PAGE, DMA_LIMIT-PAGE, 1, 3*PAGE),
            (self.base, 2**64-PAGE, PAGE, 1, 3*PAGE),
            (2**64-PAGE, PAGE, 4*PAGE, 1, 3*PAGE),
        )
        sentinel = b'Z'*self.size
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.build(*args), 0)
                self.assertEqual(c.string_at(self.base, self.size), sentinel)


if __name__ == '__main__':
    unittest.main()
