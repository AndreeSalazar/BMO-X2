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
from host.diagnostics import Rejection
from host.importers.pe import pack_pe, probe_pe


class Sbef(unittest.TestCase):
    def test_ui_profile_is_explicit_and_preserves_default_limit(self):
        from host.sbef.format import inspect
        payload=1024*1024+1
        ro_offset=((4096+payload+4095)//4096)*4096
        elf=bytearray(ro_offset+4097)
        struct.pack_into('<16sHHIQQQIHHHHHH',elf,0,b'\x7fELF\x02\x01\x01',
                         2,62,1,0x40000000,64,0,0,64,56,3,0,0,0)
        for i,(offset,address,filesz,memsz,perms) in enumerate([
            (4096,0x40000000,payload,payload,5),(ro_offset,0x40200000,1,4096,4),
            (ro_offset+4096,0x40400000,1,4096,6)]):
            struct.pack_into('<IIQQQQQQ',elf,64+56*i,1,perms,offset,address,0,filesz,memsz,4096)
        with self.assertRaises(Rejection):sbef.pack_elf(elf,abi=1)
        image=sbef.pack_elf(elf,abi=1,profile='rmlui-native-v1')
        with self.assertRaises(Rejection):inspect(image)
        self.assertEqual(len(inspect(image,profile='rmlui-native-v1')['Regions']),3)
        changed=bytearray(image);struct.pack_into('<I',changed,32+2*32+20,7)
        with self.assertRaises(Rejection):inspect(changed,profile='rmlui-native-v1')
        changed=bytearray(image);struct.pack_into('<Q',changed,32+2*32,0x40600000)
        with self.assertRaises(Rejection):inspect(changed,profile='rmlui-native-v1')
        with self.assertRaises(ValueError):inspect(image,profile='invented')
        changed=bytearray(image);changed.extend(bytes(2*1024*1024-len(changed)+1))
        with self.assertRaises(Rejection):inspect(changed,profile='rmlui-native-v1')

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
            '53424546 0200 0000 3e00 0200 63000000 0000004000000000 01000000 00000000 '
            '0000004000000000 60000000 01000000 01000000 05000000 0000000000000000 '
            '0010004000000000 61000000 02000000 00200000 06000000 0000000000000000 90 4142')
        self.assertEqual(image, expected)
        info = sbef.inspect(image)
        self.assertEqual(info['Entry'], '0x40000000')
        self.assertEqual(info['Regions'][1]['MemoryBytes'], 8192)
        versioned = sbef.pack_elf(self.elf, abi=1)
        self.assertEqual(versioned, image[:6] + b'\x01\x00' + image[8:])
        self.assertEqual(sbef.inspect(versioned)['AbiVersion'], 1)

    def test_reject_dynamic_elf_and_bad_program_headers(self):
        for offset, code, value in [(16, '<H', 3), (64, '<I', 3), (68, '<I', 7),
                                    (136, '<Q', 0x40000000), (152, '<Q', 65536)]:
            with self.subTest(offset=offset):
                changed = bytearray(self.elf)
                struct.pack_into(code, changed, offset, value)
                with self.assertRaises(ValueError):
                    sbef.pack_elf(changed)

    def test_metadata_outside_load_segments_preserves_sbef(self):
        image = sbef.pack_elf(self.elf, abi=1)
        with_metadata = self.elf + b'debug and symbol metadata outside PT_LOAD'
        self.assertEqual(sbef.pack_elf(with_metadata, abi=1), image)
        self.assertEqual(image[-3:], b'\x90AB')

    def test_producer_selector_checks_format_before_publication(self):
        with tempfile.TemporaryDirectory() as path:
            source, output = Path(path)/'app.elf', Path(path)/'app.sbef'
            source.write_bytes(self.elf)
            cli = [sys.executable, '-B', sbef.__file__, '--json-errors']
            expected = sbef.pack_elf(self.elf)
            for producer in ('clang', 'gcc', 'rustc'):
                with self.subTest(producer=producer):
                    packed = json.loads(subprocess.check_output(
                        [*cli, 'pack', str(source), str(output), '--producer', producer]))
                    probed = json.loads(subprocess.check_output(
                        [*cli, 'probe', str(source), '--producer', producer]))
                    self.assertEqual(packed['ProducerProfile'], probed['ProducerProfile'])
                    self.assertEqual(packed['ProducerProfile']['Selector'], producer)
                    self.assertFalse(packed['ProducerProfile']['IdentityAttested'])
                    self.assertEqual(output.read_bytes(), expected)
            for producer in ('msvc', 'clang-cl'):
                with self.subTest(producer=producer):
                    rejected = subprocess.run(
                        [*cli, 'pack', str(source), str(output), '--producer', producer], capture_output=True)
                    self.assertEqual(rejected.returncode, 1)
                    self.assertEqual(json.loads(rejected.stderr), dict(
                        Code='HOST-PRODUCER-FORMAT', Field=f'{producer}/PE32+', Offset=0))
                    self.assertEqual(output.read_bytes(), expected)

    def test_pack_enforces_file_and_mapped_budgets_before_publication(self):
        with tempfile.TemporaryDirectory() as path:
            source, output = Path(path)/'app.elf', Path(path)/'app.sbef'
            source.write_bytes(self.elf)
            base = [sys.executable, '-B', sbef.__file__, '--json-errors', 'pack', str(source), str(output)]
            accepted = subprocess.run([*base, '--max-file-bytes', '99', '--max-mapped-bytes', '12288'],
                                      capture_output=True, check=True)
            self.assertEqual(json.loads(accepted.stdout)['Bytes'], 99)
            original = output.read_bytes()
            for flag, field, limit, actual, offset in (
                ('--max-file-bytes', 'file_size', 98, 99, 12),
                ('--max-mapped-bytes', 'mapped_bytes', 12287, 12288, 10),
            ):
                with self.subTest(flag=flag):
                    rejected = subprocess.run([*base, flag, str(limit)], capture_output=True)
                    self.assertEqual(rejected.returncode, 1)
                    self.assertEqual(json.loads(rejected.stderr),
                                     dict(Code='SBEF-BUDGET', Field=field, Offset=offset,
                                          ActualBytes=actual, LimitBytes=limit))
                    self.assertEqual(output.read_bytes(), original)

    def test_compare_separates_file_bytes_from_mapped_pages(self):
        changed = bytearray(self.elf)
        struct.pack_into('<Q', changed, 160, 2)
        with tempfile.TemporaryDirectory() as path:
            baseline, candidate = Path(path)/'before.sbef', Path(path)/'after.sbef'
            baseline.write_bytes(sbef.pack_elf(self.elf, abi=1))
            candidate.write_bytes(sbef.pack_elf(changed, abi=1))
            compare = [sys.executable, '-B', sbef.__file__, '--json-errors',
                       'compare', str(baseline), str(candidate)]
            report = json.loads(subprocess.check_output(compare))
            self.assertEqual(report['File']['DeltaBytes'], 0)
            self.assertEqual(report['MappedRegions']['DeltaBytes'], -4096)
            self.assertEqual(report['Regions'][1]['MappedBytes']['DeltaBytes'], -4096)
            self.assertEqual(report['Regions'][1]['MemoryBytes']['DeltaBytes'], -8190)
            candidate.write_bytes(sbef.pack_elf(changed, abi=0))
            rejected = subprocess.run(compare, capture_output=True)
            self.assertEqual(rejected.returncode, 1)
            self.assertEqual(json.loads(rejected.stderr)['Code'], 'SBEF-COMPARE-ABI')

    def test_reject_truncation_permissions_overlap_and_entry(self):
        image = sbef.pack_elf(self.elf)
        for length in range(len(image)):
            with self.assertRaises(ValueError):
                sbef.inspect(image[:length])
        for offset, code, value in [(6, '<H', 2), (16, '<Q', 0x40001000), (40, '<I', 0xffffffff),
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
        image = bytearray(0x400)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 0x80)
        image[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HHIIIHH', image, 0x84, 0x8664, 1, 0, 0, 0, 128, 2)
        opt = 0x98
        struct.pack_into('<H', image, opt, 0x20b)
        struct.pack_into('<I', image, opt + 16, 0x1000)
        struct.pack_into('<Q', image, opt + 24, 0x140000000)
        struct.pack_into('<I', image, opt + 108, 2)
        struct.pack_into('<II', image, opt + 120, 0x1000, 40)
        struct.pack_into('<8sIIIIIIHHI', image, opt + 128, b'.text', 512, 0x1000,
                         512, 0x200, 0, 0, 0, 0, 0x60000000)
        struct.pack_into('<IIIII', image, 0x200, 0x1040, 0, 0, 0x1030, 0x1090)
        image[0x230:0x23d] = b'KERNEL32.dll\0'
        struct.pack_into('<QQQ', image, 0x240, 0x1080, 0x8000000000000007, 0)
        image[0x282:0x288] = b'Sleep\0'
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
            self.assertEqual(inventory['Imports'], [
                dict(DLL='KERNEL32.dll', Symbols=[dict(Name='Sleep'), dict(Ordinal=7)])
            ])
            result = subprocess.run([*base, 'pack', str(source), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr), expected)
            self.assertFalse(output.exists())
            struct.pack_into('<Q', image, 0x240, 0x1200)
            rejected = probe_pe(image)
            self.assertFalse(rejected['CanPack'])
            self.assertEqual(rejected['ImportInventoryError'], dict(
                Code='PE-IMPORT-RVA', Offset=0x240, Field='ImportByName'))

    def test_fixed_pe_keeps_exact_payload_and_rejects_invalid_layout(self):
        image = bytearray(0x400)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 0x80)
        image[0x80:0x84] = b'PE\0\0'
        opt = 0x98
        table = opt + 112
        struct.pack_into('<HHIIIHH', image, 0x84, 0x8664, 1, 0, 0, 0, 112, 3)
        struct.pack_into('<H', image, opt, 0x20b)
        struct.pack_into('<I', image, opt + 16, 0x10000)
        struct.pack_into('<QII', image, opt + 24, 0x3fff0000, 0x10000, 512)
        struct.pack_into('<II', image, opt + 56, 0x20000, 0x200)
        struct.pack_into('<H', image, opt + 68, 3)
        struct.pack_into('<8sIIIIIIHHI', image, table, b'.text', 2, 0x10000,
                         512, 0x200, 0, 0, 0, 0, 0x60000020)
        image[0x200:0x202] = bytes.fromhex('0f0b')
        self.assertTrue(probe_pe(image)['CanPack'])
        result = pack_pe(image, abi=1)
        self.assertEqual(result[64:], bytes.fromhex('0f0b'))
        self.assertEqual(sbef.inspect(result)['Regions'][0]['Permissions'], 'RX')
        lld = bytearray(image)
        lld[0x202:] = b'\xcc' * (len(lld) - 0x202)
        self.assertEqual(pack_pe(lld, abi=1), result)
        lld[-1] = 0
        with self.assertRaises(Rejection) as error:
            pack_pe(lld, abi=1)
        self.assertEqual(error.exception.code, 'PE-SECTION-PADDING')
        for offset, value, code in (
            (table + 36, 0xe0000020, 'PE-PERMISSIONS'),
            (opt + 16, 0x10002, 'PE-ENTRY'),
            (0x202, 1, 'PE-SECTION-PADDING'),
        ):
            with self.subTest(code=code):
                bad = bytearray(image)
                struct.pack_into('<I', bad, offset, value)
                with self.assertRaises(Rejection) as error:
                    pack_pe(bad, abi=1)
                self.assertEqual(error.exception.code, code)

    def test_pe64_rebases_only_internal_dir64_targets_into_sbef(self):
        image = bytearray(0x800)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 0x80)
        image[0x80:0x84] = b'PE\0\0'
        opt = 0x98
        table = opt + 240
        struct.pack_into('<HHIIIHH', image, 0x84, 0x8664, 3, 0, 0, 0, 240, 2)
        struct.pack_into('<H', image, opt, 0x20b)
        struct.pack_into('<I', image, opt + 16, 0x1000)
        struct.pack_into('<Q', image, opt + 24, 0x140000000)
        struct.pack_into('<II', image, opt + 32, 0x1000, 0x200)
        struct.pack_into('<II', image, opt + 56, 0x4000, 0x200)
        struct.pack_into('<H', image, opt + 68, 3)
        struct.pack_into('<H', image, opt + 70, 0x40)
        struct.pack_into('<I', image, opt + 108, 16)
        struct.pack_into('<II', image, opt + 112 + 5 * 8, 0x3000, 12)
        sections = (
            (b'.text', 0x100, 0x1000, 0x200, 0x200, 0x60000020),
            (b'.data', 0x100, 0x2000, 0x200, 0x400, 0xC0000040),
            (b'.reloc', 12, 0x3000, 0x200, 0x600, 0x40000040),
        )
        for index, (name, virtual, rva, raw, offset, flags) in enumerate(sections):
            struct.pack_into('<8sIIIIIIHHI', image, table + index * 40, name, virtual,
                             rva, raw, offset, 0, 0, 0, 0, flags)
        image[0x200] = 0xC3
        struct.pack_into('<Q', image, 0x420, 0x140001000)
        struct.pack_into('<IIHH', image, 0x600, 0x2000, 12, 0xA020, 0)

        probe = probe_pe(image)
        self.assertTrue(probe['CanPack'], probe['Blockers'])
        self.assertEqual(probe['Relocations']['Count'], 1)
        packed = pack_pe(image, abi=1)
        info = sbef.inspect(packed)
        self.assertEqual(info['Entry'], '0x40001000')
        data_region = info['Regions'][1]
        self.assertEqual(struct.unpack_from('<Q', packed, data_region['Offset'] + 0x20)[0],
                         0x40001000)

        unsupported = bytearray(image)
        struct.pack_into('<H', unsupported, 0x608, 0x3020)
        rejected = probe_pe(unsupported)
        self.assertFalse(rejected['CanPack'])
        self.assertEqual(rejected['RelocationInventoryError']['Code'], 'PE-RELOCATION-TYPE')

        without_table = bytearray(image)
        struct.pack_into('<II', without_table, opt + 112 + 5 * 8, 0, 0)
        rejected = probe_pe(without_table)
        self.assertFalse(rejected['CanPack'])
        self.assertEqual(rejected['Blockers'][0]['Code'], 'PE-RELOCATIONS-MISSING')


if __name__ == '__main__':
    unittest.main()
