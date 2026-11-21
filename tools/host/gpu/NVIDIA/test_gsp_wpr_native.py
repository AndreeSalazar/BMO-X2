"""Execute the Ring 0 WPR writer against the measured GA106 handoff."""

import ctypes as c
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from .gsp_wpr import decode_bootlog, encode, ga106_cold_vram
from .test_gsp_wpr import BOOTLOG


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get('ProgramFiles','C:/Program Files'))/'LLVM/bin'
PAGE = 4096
MEASURED = (0x00008b8f,0x000003ff,0x3000,1,0x0045cb8f,0x00100000,0x02effff0,0)
WPR_OFFSET = 6883*PAGE
WPR_IOVA = 0x0a106000
LEAF_OFFSET = (6620+229)*PAGE
LEAF_ENTRY = LEAF_OFFSET+262*8

SOURCE = r"""
#define BMO_NVIDIA_GSP_PREPARE
#define BMO_NVIDIA_GSP_QUEUES
#define BMO_NVIDIA_GSP_LIBOS
#define BMO_NVIDIA_GSP_BOOT_CHAIN
#define BMO_GSP_IMAGE_BYTES 26992640
#define BMO_GSP_FILE_BYTES 27179160
#define BMO_GSP_BOOT_FILE_OFFSET 27043992
#define BMO_GSP_BOOT_PAGES 33
#define BMO_GSP_MONITOR_BYTES 24576
#define BMO_GSP_MONITOR_CODE 6144
#define BMO_GSP_MONITOR_DATA 2048
#define BMO_GSP_MONITOR_MANIFEST 0
#include "kernel/drivers/GPU/NVIDIA/gsp_layout.inc"
.text
.globl wpr_fixture
wpr_fixture:
    push %rbp
    push %rsi
    push %rdi
    mov %rcx, %rbp
    mov %rdx, %r9
    call nvidia_gsp_prepare_wpr
    pop %rdi
    pop %rsi
    pop %rbp
    ret
#include "kernel/drivers/GPU/NVIDIA/gsp_wpr_prepare.inc"
"""


@unittest.skipUnless(os.name=='nt','requires Windows and LLVM')
class NvidiaWprNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from _ctypes import FreeLibrary

        folder = tempfile.TemporaryDirectory(prefix='bmo-wpr-')
        cls.addClassCleanup(folder.cleanup)
        directory = Path(folder.name)
        source, obj, dll = directory/'probe.S', directory/'probe.obj', directory/'probe.dll'
        source.write_text(SOURCE,encoding='ascii')
        subprocess.run([LLVM/'clang.exe','--target=x86_64-pc-windows-msvc','-I',ROOT,'-c',source,'-o',obj],check=True)
        subprocess.run([LLVM/'lld-link.exe','/dll','/noentry','/nodefaultlib','/export:wpr_fixture',
                        f'/out:{dll}',obj],check=True)
        cls.library = c.WinDLL(str(dll))
        cls.addClassCleanup(FreeLibrary,cls.library._handle)
        cls.prepare = cls.library.wpr_fixture
        cls.prepare.argtypes = [c.c_void_p,c.c_void_p]
        cls.prepare.restype = None

    def run_sample(self, values):
        context = bytearray(4096)
        struct.pack_into('<8I',context,0x8d0,*values)
        storage = c.create_string_buffer(WPR_OFFSET+2*PAGE)
        base = (c.addressof(storage)+PAGE-1)&-PAGE
        self.prepare((c.c_ubyte*len(context)).from_buffer(context),base)
        return context,c.string_at(base+WPR_OFFSET,PAGE),struct.unpack('<Q',c.string_at(base+LEAF_ENTRY,8))[0],base

    def test_metal_sample_matches_host_encoder(self):
        report = decode_bootlog(BOOTLOG+'WPR='+','.join(f'{word:08X}' for word in MEASURED))
        self.assertEqual(report['mmu_locked_pages'],[0x10000000,0x2effff000])
        expected, ranges = encode(vram=ga106_cold_vram(report),
            firmware=dict(image_bytes=26992640,boot_bytes=24576,signature_bytes=PAGE,
                          monitor_offsets=dict(manifest=0,data=2048,code=6144)),
            radix_iova=0x099bf000,boot_iova=0x0a0e5000,signature_iova=0x099be000)
        context, page, pte, base = self.run_sample(MEASURED)
        self.assertEqual(ranges['frts'],[0x2ffe00000,0x2fff00000])
        self.assertEqual(page,expected+bytes(PAGE-len(expected)))
        self.assertEqual(pte,(base+WPR_OFFSET)|0x6000000000000001)
        self.assertEqual(struct.unpack_from('<Q',context,0x8f0)[0],WPR_IOVA)
        self.assertEqual(struct.unpack_from('<I',context,0x814)[0],6)

    def test_live_wpr_incomplete_gfw_and_pri_errors_leave_no_mapping(self):
        for index, value in ((0,0),(1,0x20),(1,0xbad000ff),(3,0xffffffff),(7,0x10)):
            sample = list(MEASURED)
            sample[index] = value
            with self.subTest(index=index,value=value):
                context,page,pte,_ = self.run_sample(sample)
                self.assertEqual(page,bytes(PAGE))
                self.assertEqual(pte,0)
                self.assertEqual(struct.unpack_from('<Q',context,0x8f0)[0],0)

    def test_relocates_a_low_vga_workspace(self):
        sample = list(MEASURED)
        sample[3] = 0x010ff008
        _,page,_,_ = self.run_sample(sample)
        self.assertEqual(struct.unpack_from('<Q',page,184)[0],(12<<30)-(128<<10))
