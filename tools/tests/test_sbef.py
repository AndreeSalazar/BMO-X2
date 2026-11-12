"""Provisional SBEF reader and producer acceptance boundaries."""
from pathlib import Path
import json
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sbef
from sbef_host.diagnostics import Rejection


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

    def test_diagnostic_points_to_source_field(self):
        dynamic = bytearray(self.elf)
        struct.pack_into('<I', dynamic, 64, 3)
        with self.assertRaises(Rejection) as error:
            sbef.pack_elf(dynamic)
        self.assertEqual(error.exception.report(),
                         dict(Code='ELF-INTERPRETER', Offset=64, Field='p_type', RegionIndex=0))
        image = bytearray(sbef.pack_elf(self.elf))
        struct.pack_into('<I', image, 52, 7)
        with self.assertRaises(Rejection) as error:
            sbef.inspect(image)
        self.assertEqual(error.exception.report(),
                         dict(Code='SBEF-PERMISSIONS', Offset=52, Field='permissions', RegionIndex=0))

    def test_pe_probe_reports_imports_and_pack_rejects(self):
        image = bytearray(0x204)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 0x80)
        image[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HHIIIHH', image, 0x84, 0x8664, 1, 0, 0, 0, 128, 2)
        opt = 0x98
        struct.pack_into('<H', image, opt, 0x20b)
        struct.pack_into('<I', image, opt + 16, 0x1000)
        struct.pack_into('<Q', image, opt + 24, 0x140000000)
        struct.pack_into('<I', image, opt + 108, 2)
        struct.pack_into('<II', image, opt + 120, 0x1000, 4)
        struct.pack_into('<8sIIIIIIHHI', image, opt + 128, b'.text', 4, 0x1000,
                         4, 0x200, 0, 0, 0, 0, 0x60000000)
        with tempfile.TemporaryDirectory() as path:
            source, output = Path(path)/'app.exe', Path(path)/'app.sbef'
            source.write_bytes(image)
            base = [sys.executable, '-B', sbef.__file__, '--json-errors']
            probe = subprocess.run([*base, 'probe', str(source)], capture_output=True, check=True)
            inventory = json.loads(probe.stdout)
            self.assertFalse(inventory['CanPack'])
            self.assertTrue(inventory['Sections'][0]['Executable'])
            expected = dict(Code='PE-IMPORTS', Offset=opt + 120, Field='DataDirectory.imports')
            self.assertEqual(inventory['Blockers'], [expected])
            result = subprocess.run([*base, 'pack', str(source), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr), expected)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
