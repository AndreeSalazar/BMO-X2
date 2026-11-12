"""Provisional SBEF reader and producer acceptance boundaries."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sbef


class Sbef(unittest.TestCase):
    def setUp(self):
        elf = bytearray(8194)
        struct.pack_into('<16sHHIQQQIHHHHHH', elf, 0, b'\x7fELF\x02\x01\x01',
                         2, 62, 1, 0x40000000, 64, 0, 0, 64, 56, 2, 0, 0, 0)
        struct.pack_into('<IIQQQQQQ', elf, 64, 1, 5, 4096, 0x40000000, 0, 1, 1, 4096)
        struct.pack_into('<IIQQQQQQ', elf, 120, 1, 6, 8192, 0x40001000, 0, 2, 8192, 4096)
        elf[4096] = 0x90
        elf[8192:] = b'AB'
        self.elf = elf

    def test_exact_header_regions_and_payload(self):
        image = sbef.pack_elf(self.elf)
        expected = bytes.fromhex(
            '53424546 0100 0000 3e00 0200 63000000 0000004000000000 00000000 00000000 '
            '0000004000000000 60000000 01000000 01000000 05000000 0000000000000000 '
            '0010004000000000 61000000 02000000 00200000 06000000 0000000000000000 90 4142')
        self.assertEqual(image, expected)
        info = sbef.inspect(image)
        self.assertEqual(info['Entry'], '0x40000000')
        self.assertEqual(info['Regions'][1]['MemoryBytes'], 8192)

    def test_reject_dynamic_elf_and_bad_program_headers(self):
        for offset, code, value in [(16, '<H', 3), (64, '<I', 3), (68, '<I', 7),
                                    (136, '<Q', 0x40000000), (152, '<Q', 65536)]:
            with self.subTest(offset=offset):
                changed = bytearray(self.elf)
                struct.pack_into(code, changed, offset, value)
                with self.assertRaises(ValueError):
                    sbef.pack_elf(changed)

    def test_reject_truncation_permissions_overlap_and_entry(self):
        image = sbef.pack_elf(self.elf)
        for length in range(len(image)):
            with self.assertRaises(ValueError):
                sbef.inspect(image[:length])
        for offset, code, value in [(6, '<H', 1), (16, '<Q', 0x40001000), (40, '<I', 0xffffffff),
                                    (52, '<I', 7), (64, '<Q', 0x40000000), (80, '<I', 0xffffffff)]:
            with self.subTest(offset=offset):
                changed = bytearray(image)
                struct.pack_into(code, changed, offset, value)
                with self.assertRaises(ValueError):
                    sbef.inspect(changed)


if __name__ == '__main__':
    unittest.main()
