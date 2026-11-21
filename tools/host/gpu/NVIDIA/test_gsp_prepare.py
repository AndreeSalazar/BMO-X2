"""Exercise the optional Ring 0 code with controlled EFI handoff data on HOST."""

import ctypes as c
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'
PAGE = 4096
FILE_BYTES = 0x3500
IMAGE_OFFSET = 64
IMAGE_BYTES = 8192
SIGNATURE_OFFSET = 0x23c0
PAGES = 8
IOVA = 0x08000000
RADIX_IOVA = IOVA+3*PAGE
FIXTURE = r"""
.text
.globl prepare_fixture
prepare_fixture:
    push %rbp
    push %rsi
    push %rdi
    mov %rcx, %rbp
    call .Lgsp_prepare_begin
    pop %rdi
    pop %rsi
    pop %rbp
    ret
#include "kernel/drivers/GPU/NVIDIA/gsp_layout.inc"
#include "kernel/drivers/GPU/NVIDIA/gsp_prepare.inc"
"""


@unittest.skipUnless(os.name == 'nt', 'requires Windows and LLVM')
class NvidiaGspPrepare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix='bmo-gsp-prepare-')
        cls.addClassCleanup(folder.cleanup)
        directory = Path(folder.name)
        source, obj, dll = directory/'probe.S', directory/'probe.obj', directory/'probe.dll'
        source.write_text(FIXTURE, encoding='ascii')
        subprocess.run([LLVM/'clang.exe','--target=x86_64-pc-windows-msvc',
                        '-DBMO_NVIDIA_GSP_PREPARE',
                        f'-DBMO_GSP_FILE_BYTES={FILE_BYTES}', f'-DBMO_GSP_IMAGE_OFFSET={IMAGE_OFFSET}',
                        f'-DBMO_GSP_IMAGE_BYTES={IMAGE_BYTES}', f'-DBMO_GSP_SIGNATURE_OFFSET={SIGNATURE_OFFSET}',
                        '-I', ROOT, '-c', source, '-o', obj], check=True)
        subprocess.run([LLVM/'lld-link.exe','/dll','/noentry','/nodefaultlib','/export:prepare_fixture',
                        f'/out:{dll}',obj],check=True)
        cls.library = c.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary, cls.library._handle)
        cls.prepare = cls.library.prepare_fixture
        cls.prepare.argtypes = [c.c_void_p]
        cls.prepare.restype = None

        kernel = c.WinDLL('kernel32', use_last_error=True)
        allocate = kernel.VirtualAlloc
        allocate.argtypes = [c.c_void_p,c.c_size_t,c.c_uint32,c.c_uint32]
        allocate.restype = c.c_void_p
        free = kernel.VirtualFree
        free.argtypes = [c.c_void_p,c.c_size_t,c.c_uint32]
        free.restype = c.c_int
        # The tested entry accepts RAM below 256 MiB, as the boot context does.
        for address in range(0x4000000,0xe000000,0x1000000):
            cls.base = allocate(address,PAGES*PAGE,0x3000,4)
            if cls.base:
                cls.addClassCleanup(free,cls.base,0,0x8000)
                break
        else:
            raise OSError('No low-address range for the GSP handoff fixture')

    def setUp(self):
        self.context = bytearray(0x2000)
        self.mapping = (c.c_ubyte*len(self.context)).from_buffer(self.context)
        self.image = bytes(range(256))*(IMAGE_BYTES//256)
        self.signature = bytes(range(255,-1,-1))*(PAGE//256)
        raw = bytearray(b'\xc3'*(PAGES*PAGE))
        raw[IMAGE_OFFSET:IMAGE_OFFSET+IMAGE_BYTES] = self.image
        raw[SIGNATURE_OFFSET:SIGNATURE_OFFSET+PAGE] = self.signature
        self.raw = bytes(raw)
        c.memmove(self.base,self.raw,len(self.raw))
        struct.pack_into('<Q8xQ',self.context,0x50,48,48)
        struct.pack_into('<QQI',self.context,0x800,self.base,FILE_BYTES,5)
        self.descriptor(2,PAGES)

    def descriptor(self, kind, pages):
        struct.pack_into('<I4xQQQ',self.context,0x1000,kind,self.base,0,pages)

    def status(self):
        return struct.unpack_from('<I4Q',self.context,0x814)

    def test_aligns_both_slices_without_a_second_copy(self):
        self.prepare(self.mapping)
        root = self.base+6*PAGE
        tail = bytearray(5*PAGE)
        struct.pack_into('<Q',tail,0,RADIX_IOVA+PAGE)
        struct.pack_into('<Q',tail,PAGE,RADIX_IOVA+2*PAGE)
        struct.pack_into('<2Q',tail,2*PAGE,IOVA,IOVA+PAGE)
        read = 1<<61
        struct.pack_into('<Q',tail,3*PAGE+(IOVA>>21)*8,(root+PAGE)|read|0x201)
        for page in range(6):
            struct.pack_into('<Q',tail,4*PAGE+page*8,(self.base+page*PAGE)|read|1)
        after = self.image + self.signature + tail
        self.assertEqual(self.status(),(3,self.base,self.base+IMAGE_BYTES,RADIX_IOVA,root))
        self.assertEqual(c.string_at(self.base,len(self.raw)),after)
        self.prepare(self.mapping)
        self.assertEqual(c.string_at(self.base,len(self.raw)),after)

    def test_rejects_unowned_or_short_ranges(self):
        self.descriptor(7,PAGES)
        self.prepare(self.mapping)
        self.assertEqual(self.status(),(1,0,0,0,0))
        self.assertEqual(c.string_at(self.base,len(self.raw)),self.raw)
        struct.pack_into('<I',self.context,0x814,0)
        self.descriptor(2,PAGES-1)
        self.prepare(self.mapping)
        self.assertEqual(self.status(),(1,0,0,0,0))
        self.assertEqual(c.string_at(self.base,len(self.raw)),self.raw)

    def test_skips_unstaged_firmware(self):
        struct.pack_into('<I',self.context,0x810,4)
        self.prepare(self.mapping)
        self.assertEqual(self.status(),(0,0,0,0,0))
        self.assertEqual(c.string_at(self.base,len(self.raw)),self.raw)


if __name__ == '__main__':
    unittest.main()
