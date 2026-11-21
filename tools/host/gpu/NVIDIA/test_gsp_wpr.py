"""Verify WPR offsets and reject unfit VRAM and DMA ranges."""

import struct
import unittest

from .gsp_wpr import MIB, decode_bootlog, encode


BOOTLOG = ('BMO-X2 DESKTOP UEFI PRE-EBS\nGPU_NVIDIA_ID=250410DE\n'
           'GPU_NVIDIA_CMD=00000003\nGPU_MMIO_STATUS=00000008\n')
WPR = 'WPR=00000001,000000FF,00003000,02FFF008,00000001,00000010,00000000,00000000\n'


class GspWprTest(unittest.TestCase):
    def setUp(self):
        self.arguments = dict(
            vram=dict(bytes=12288*MIB, workspace_start=0x2fff00000, locked_start=None,
                      permitted_start=0x2f0000000, end_margin=0, frts_bytes=MIB,
                      heap_bytes=128*MIB, non_wpr_heap_bytes=MIB),
            firmware=dict(image_bytes=0x19be000, boot_bytes=0x6000, signature_bytes=0x1000,
                          monitor_offsets=dict(manifest=0,data=0x800,code=0x1800)),
            radix_iova=0x099bf000, boot_iova=0x0a0e5000, signature_iova=0x099be000)

    def test_ga10x_cold_boot_layout(self):
        data, ranges = encode(**self.arguments)
        self.assertEqual(len(data),256)
        self.assertEqual(struct.unpack_from('<11Q',data),(
            0xdc3aae21371a60b3,1,0x099bf000,0x19be000,0x0a0e5000,0x6000,
            0x1800,0x800,0,0x099be000,0x1000))
        self.assertEqual(ranges['wpr'],[0x2f6300000,0x2fff00000])
        self.assertEqual(ranges['frts'],[0x2ffe00000,0x2fff00000])
        self.assertEqual(ranges['firmware'][0],0x2fe430000)
        self.assertEqual(data[200:],bytes(56))

    def test_respects_the_lower_of_vga_and_mmu_lock(self):
        self.arguments['vram'].update(locked_start=0x2ffd20000,end_margin=MIB)
        _, ranges = encode(**self.arguments)
        self.assertEqual(ranges['wpr'][1],0x2ffc20000)

    def test_rejects_when_wpr_overlaps_live_vram(self):
        self.arguments['vram']['permitted_start']=0x2f7200000
        with self.assertRaisesRegex(ValueError, 'WPR no cabe'):
            encode(**self.arguments)
        self.arguments['vram']['locked_start']=0
        with self.assertRaisesRegex(ValueError, 'region reservada'):
            encode(**self.arguments)

    def test_rejects_overlap_with_the_radix3_directory(self):
        self.arguments['boot_iova']=self.arguments['radix_iova']+4096
        with self.assertRaisesRegex(ValueError, 'se solapan'):
            encode(**self.arguments)

    def test_decodes_measured_vram_and_distinguishes_no_lock(self):
        report = decode_bootlog(BOOTLOG+WPR)
        self.assertEqual(report['vram_bytes'],12288*MIB)
        self.assertEqual(report['workspace_start'],0x2fff00000)
        self.assertIsNone(report['mmu_locked_pages'])
        self.assertFalse(report['wpr2_active'])

    def test_reports_active_wpr_and_the_zero_mmu_page(self):
        report = decode_bootlog(BOOTLOG+WPR.replace('00000010,00000000,00000000',
                                                     '00000000,00000000,02FFF000'))
        self.assertEqual(report['mmu_locked_pages'],[0,0])
        self.assertTrue(report['wpr2_active'])

    def test_rejects_incomplete_or_privileged_samples(self):
        for sample in ('', WPR.replace('00003000','--------'), WPR.replace('000000FF','BAD000FF'),
                       WPR.replace('02FFF008,00000001','02FFF008,00000000')):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                decode_bootlog(BOOTLOG+sample)
        with self.assertRaisesRegex(ValueError, 'PCI Command'):
            decode_bootlog(BOOTLOG.replace('00000003','00000007')+WPR)
