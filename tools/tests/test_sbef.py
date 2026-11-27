"""Provisional SBEF reader and producer acceptance boundaries."""
from pathlib import Path
import hashlib
from io import BytesIO
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sbef
from host.diagnostics import Rejection
from host.importers.pe import DIRECTORIES, pack_pe, probe_pe
from host.importers.pe_load_config import inventory_load_config
from host.importers.pe_unwind import inventory_unwind
from host.pe_admission import explain_pe
from host.toolchains.windows_catalog import import_coverage


class Sbef(unittest.TestCase):
    def test_pe_admission_explains_scoped_imports_iat_and_security(self):
        inventory = dict(
            CanPack=False,
            Blockers=[dict(Code=code, Offset=16, Field=field) for code, field in (
                ('PE-IMPORTS', 'imports'), ('PE-LOAD-CONFIG', 'load_config'), ('PE-IAT', 'iat'))],
            Imports=[
                dict(DLL='kernel32.DLL', Symbols=[dict(Name='GetCommandLineW'), dict(Name='ExitProcess'),
                                                  dict(Name='VirtualProtect'), dict(Ordinal=8)]),
                dict(DLL='example.dll', Symbols=[dict(Name='GetCommandLineW')]),
            ],
            Directories=dict(iat=dict(RVA=4096, Bytes=48)),
            LoadConfigInventory=dict(SecurityCookieVA=4096, GuardFlags=0x100, GuardCFDispatchFunctionPointerVA=4104),
        )
        report = explain_pe(inventory)
        self.assertEqual(report['Status'], 'blocked')
        self.assertEqual(report['Imports']['Counts'], dict(available_in_fixture=2, missing=2, ordinal=1))
        process = next(group for group in report['Imports']['Groups'] if group['Name'] == 'Arranque y entorno')
        self.assertEqual(process['Imports'][0]['Fixtures'], [
            dict(Profile='win64-process-start-v1', Target='bmo_get_command_line_w')
        ])
        self.assertIn('cookie de seguridad', report['Blockers'][1]['Required'])
        self.assertIn('CFG', report['Blockers'][1]['Required'])
        self.assertEqual(report['Blockers'][2]['Observed'], dict(RVA=4096, Bytes=48))

    def test_load_config_inventory_respects_structure_size_and_cookie_permissions(self):
        data = bytearray(160)
        base = 0x140000000
        directory = dict(RVA=0x1000, Bytes=len(data))
        sections = [
            dict(RVA=0x1000, VirtualBytes=len(data), FileBytes=len(data), FileOffset=0,
                 Writable=False, Executable=False),
            dict(RVA=0x2000, VirtualBytes=16, FileBytes=0, FileOffset=0,
                 Writable=True, Executable=False),
        ]
        struct.pack_into('<I', data, 0, 148)
        struct.pack_into('<Q', data, 88, base + 0x2008)
        struct.pack_into('<QI', data, 136, 3, 0x500)
        report = inventory_load_config(data, sections, directory, base, 0x180)
        self.assertEqual(report['SecurityCookieRVA'], 0x2008)
        self.assertTrue(report['SecurityCookieWritableNonExecutable'])
        self.assertEqual(report['GuardCFFunctionCount'], 3)
        self.assertEqual(report['RecognizedGuardFlags'], ['CF_INSTRUMENTED', 'CF_FUNCTION_TABLE_PRESENT'])
        struct.pack_into('<Q', data, 88, base + 0x2009)
        self.assertFalse(inventory_load_config(data, sections, directory, base, 0x180)
                         ['SecurityCookieWritableNonExecutable'])
        struct.pack_into('<I', data, 0, 96)
        self.assertIsNone(inventory_load_config(data, sections, directory, base, 0x180)['GuardFlags'])
        struct.pack_into('<I', data, 0, len(data) + 1)
        with self.assertRaises(Rejection) as rejected:
            inventory_load_config(data, sections, directory, base, 0x180)
        self.assertEqual(rejected.exception.code, 'PE-LOAD-CONFIG-INVENTORY-SIZE')

    def test_producer_work_plan_has_evidence_and_filters_markdown(self):
        command = [sys.executable, '-B', sbef.__file__, 'profiles']
        report = json.loads(subprocess.check_output(command))
        work = report['ProducerWorkPlan']
        self.assertEqual(list(work), ['msvc', 'clang-cl', 'clang', 'gcc', 'rustc'])
        self.assertEqual(set(work), {profile['Selector'] for profile in report['Profiles']})
        root = Path(sbef.__file__).resolve().parents[1]
        for producer in work.values():
            self.assertTrue(producer['Milestones'])
            for _, path in producer['Evidence']:
                self.assertTrue((root / path).is_file(), path)
        all_markdown = subprocess.check_output([*command, '--format', 'markdown'], text=True)
        self.assertLess(all_markdown.index('## msvc'), all_markdown.index('## clang-cl'))
        gcc = [*command, '--producer', 'gcc']
        self.assertEqual(list(json.loads(subprocess.check_output(gcc))['ProducerWorkPlan']), ['gcc'])
        gcc_markdown = subprocess.check_output([*gcc, '--format', 'markdown'], text=True)
        self.assertIn('Doom con GCC', gcc_markdown)
        self.assertNotIn('## msvc', gcc_markdown)

    def test_unwind_inventory_reports_handlers_and_rejects_invalid_handler_rva(self):
        data = bytearray(0x100)
        sections = [
            dict(RVA=0x1000, FileOffset=0, VirtualBytes=0x80, FileBytes=0x80, Executable=True),
            dict(RVA=0x2000, FileOffset=0x80, VirtualBytes=0x80, FileBytes=0x80, Executable=False),
        ]
        directory = dict(RVA=0x2000, Bytes=36)
        struct.pack_into('<9I', data, 0x80, 0x1000, 0x1010, 0x2030, 0x1010, 0x1020, 0x2040,
                         0x1020, 0x1030, 0x2060)
        struct.pack_into('<4BI', data, 0xb0, 0x19, 0, 0, 0, 0x1060)
        struct.pack_into('<4BHH3I', data, 0xc0, 0x21, 0, 1, 0, 0, 0, 0x1000, 0x1010, 0x2030)
        data[0xe0] = 2
        report = inventory_unwind(data, sections, directory, 0x180)
        self.assertEqual(report['Versions'], {1: 2, 2: 1})
        self.assertEqual(report['V1ExceptionHandlerCount'], 1)
        self.assertEqual(report['V1TerminationHandlerCount'], 1)
        self.assertEqual(report['V1ChainedCount'], 1)
        self.assertEqual(report['V1Handlers'], [dict(RVA=0x1060, FunctionCount=1)])
        struct.pack_into('<I', data, 0xb4, 0x2070)
        with self.assertRaises(Rejection) as rejected:
            inventory_unwind(data, sections, directory, 0x180)
        self.assertEqual(rejected.exception.code, 'PE-UNWIND-INVENTORY-RVA')

    def test_msvc_catalog_filters_and_points_to_existing_evidence(self):
        command = [sys.executable, '-B', sbef.__file__, 'profiles']
        general = json.loads(subprocess.check_output(command))
        self.assertEqual(len(general['Profiles']), 5)
        self.assertIn('CapabilityCatalog', general)
        msvc = [*command, '--producer', 'msvc']
        report = json.loads(subprocess.check_output(msvc))
        groups = {group['Id']: group['Capabilities'] for group in report['CapabilityGroups']}
        self.assertEqual([item['Id'] for item in groups['directories']],
                         [name for name, _ in DIRECTORIES.values()])
        root = Path(sbef.__file__).resolve().parents[1]
        for item in (item for group in groups.values() for item in group):
            self.assertIn(item['State'], report['CapabilityStates'])
            if item['State'] == 'qemu':
                self.assertTrue((root / item['Evidence']).is_file(), item)
        filtered = json.loads(subprocess.check_output([*msvc, '--category', 'tls-exceptions']))
        self.assertEqual([group['Id'] for group in filtered['CapabilityGroups']], ['tls-exceptions'])
        markdown = subprocess.check_output([*msvc, '--category', 'tls-exceptions', '--format', 'markdown'], text=True)
        self.assertIn('## TLS, hilos y excepciones', markdown)
        self.assertIn('[Evidencia](Reports/host-msvc-tls-qemu.json)', markdown)
        self.assertNotIn('## Imports y DLL', markdown)
        invalid = subprocess.run([*command, '--producer', 'gcc', '--category', 'runtime'],
                                 capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)

    def test_windows_dependency_levels_and_exact_fixture_symbol_matching(self):
        command = [sys.executable, '-B', sbef.__file__, 'profiles', '--producer', 'msvc']
        catalog = json.loads(subprocess.check_output([*command, '--windows-level', 'todos']))
        self.assertEqual([level['Level'] for level in catalog['WindowsImportCatalog']],
                         ['base', 'intermedio', 'avanzado'])
        names = [dll for level in catalog['WindowsImportCatalog']
                 for group in level['Groups'] for dll in group['DLLs']]
        self.assertEqual(len(names), len(set(names)))
        markdown = subprocess.check_output(
            [*command, '--windows-level', 'avanzado', '--format', 'markdown'], text=True)
        self.assertIn('`d3d12.dll`', markdown)
        self.assertNotIn('`kernel32.dll`', markdown)
        coverage = import_coverage([
            dict(DLL='Kernel32.DLL', Symbols=[dict(Name='WriteFile'), dict(Name='writefile'), dict(Ordinal=7)]),
            dict(DLL='API-MS-Win-CRT-stdio-l1-1-0.dll', Symbols=[dict(Name='printf')]),
            dict(DLL='custom.dll', Symbols=[dict(Name='WriteFile')]),
        ])
        self.assertEqual(coverage['SymbolCount'], 5)
        self.assertEqual(coverage['FixtureSymbolCount'], 1)
        self.assertEqual(coverage['PendingSymbolCount'], 4)
        core, crt, unknown = coverage['Libraries']
        self.assertEqual(core['FixtureSymbols'], [dict(Name='WriteFile', Target='bmo_session_write')])
        self.assertEqual(core['PendingSymbols'], [dict(Name='writefile'), dict(Ordinal=7)])
        self.assertEqual((crt['Level'], crt['Group']), ('base', 'crt'))
        self.assertIsNone(unknown['Group'])

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

    def test_catalog_classifies_by_content_and_pack_checks_reviewed_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'renamed.txt'
            source.write_bytes(self.elf)
            (root / 'broken.exe').write_bytes(b'MZ')
            (root / 'opaque.bin').write_bytes(b'\x00\xff')
            (root / 'usage.md').write_text('Text only', encoding='utf-8')
            (root / 'code.py').write_text('raise RuntimeError()', encoding='utf-8')
            cli = [sys.executable, '-B', sbef.__file__, '--json-errors']
            report = json.loads(subprocess.check_output([*cli, 'catalog', str(root)]))
            files = {file['Path']: file for file in report['Files']}
            self.assertEqual(report['Categories']['DESCONOCIDO'], ['broken.exe', 'opaque.bin'])
            self.assertEqual(report['Categories']['FUENTE'], ['code.py'])
            self.assertEqual(report['Categories']['DATOS'], ['usage.md'])
            self.assertTrue(files['renamed.txt']['ExtensionMismatch'])
            self.assertEqual(files['broken.exe']['Rejection']['Code'], 'PE-DOS-HEADER')
            digest = hashlib.sha256(self.elf).hexdigest()
            self.assertEqual(files['renamed.txt']['SHA256'], digest)
            output = root / 'app.sbef'
            pack = [*cli, 'pack', str(source), str(output), '--expected-sha256', digest.upper()]
            packed = json.loads(subprocess.check_output(pack))
            self.assertEqual(packed['ReviewedInputSHA256'], digest)
            self.assertEqual(output.read_bytes(), sbef.pack_elf(self.elf))
            source.write_bytes(self.elf + b'changed after review')
            rejected = subprocess.run(pack, capture_output=True)
            self.assertEqual(rejected.returncode, 1)
            self.assertEqual(json.loads(rejected.stderr),
                             dict(Code='HOST-CATALOG-HASH', Field='input', Offset=0))
            self.assertEqual(output.read_bytes(), sbef.pack_elf(self.elf))

    def test_deep_catalog_reads_zip_members_with_limits_and_keeps_paths_virtual(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inner = BytesIO()
            with zipfile.ZipFile(inner, 'w') as nested:
                nested.writestr('readme.txt', b'nested file')
            bundle = root / 'assets.zip'
            with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('bin/pretend.txt', self.elf)
                archive.writestr('resources.pak', bytes(2 * 1024 * 1024 + 1))
                archive.writestr('../outside.txt', b'not extracted')
                archive.writestr('a.dll', b'first')
                archive.writestr('A.dll', b'second')
                archive.writestr('nested.zip', inner.getvalue())
                archive.writestr('manual.txt.exe', self.elf)
            (root / 'launcher.pdf.exe').write_bytes(self.elf)
            (root / 'broken.zip').write_bytes(b'PK\x03\x04')
            crc_bundle = BytesIO()
            with zipfile.ZipFile(crc_bundle, 'w') as archive:
                archive.writestr('original.txt', b'integrity marker')
            (root / 'bad-crc.zip').write_bytes(crc_bundle.getvalue().replace(b'integrity marker', b'gntegrity marker'))
            cli = [sys.executable, '-B', sbef.__file__, 'catalog', str(root), '--deep']
            report = json.loads(subprocess.check_output(cli))
            files = {item['Path']: item for item in report['Files']}
            archive = files['assets.zip']['Archive']
            entries = {item['Path']: item for item in archive['Entries']}
            self.assertEqual(archive['Status'], 'REVISION')
            self.assertEqual(archive['DeclaredEntries'], 7)
            self.assertEqual(entries['bin/pretend.txt']['Category'], 'EJECUTABLE')
            self.assertTrue(entries['bin/pretend.txt']['ExtensionMismatch'])
            self.assertTrue(entries['bin/pretend.txt']['SHA256'])
            self.assertIn('RUTA_DE_ARCHIVO_NO_ADMITIDA', entries['../outside.txt']['Findings'])
            self.assertIn('NOMBRE_DUPLICADO', entries['a.dll']['Findings'])
            self.assertIn('NOMBRE_DUPLICADO', entries['A.dll']['Findings'])
            self.assertNotIn('SHA256', entries['resources.pak'])
            self.assertEqual(entries['nested.zip']['Archive']['Entries'][0]['Category'], 'DATOS')
            self.assertIn('DOBLE_EXTENSION_EJECUTABLE', entries['manual.txt.exe']['NameFindings'])
            self.assertEqual(files['broken.zip']['Archive']['Status'], 'REVISION')
            crc_entry = files['bad-crc.zip']['Archive']['Entries'][0]
            self.assertNotIn('SHA256', crc_entry)
            self.assertIn('integridad', crc_entry['Reason'])
            self.assertIn('DOBLE_EXTENSION_EJECUTABLE', files['launcher.pdf.exe']['NameFindings'])
            self.assertIn('launcher.pdf.exe', report['RoleGroups']['LANZADOR_O_INSTALADOR'])
            self.assertTrue(report['LaunchCandidates'][0]['RequiresReview'])
            self.assertEqual(report['Coverage']['ArchiveMembersListed'], 9)
            self.assertEqual(sorted(item.name for item in root.iterdir()),
                             ['assets.zip', 'bad-crc.zip', 'broken.zip', 'launcher.pdf.exe'])

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

    def test_pe32_game_catalog_reports_architecture_without_win64_coverage(self):
        image = bytearray(0x400)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 0x80)
        image[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HHIIIHH', image, 0x84, 0x14c, 1, 0, 0, 0, 112, 2)
        opt = 0x98
        struct.pack_into('<H', image, opt, 0x10b)
        struct.pack_into('<I', image, opt + 16, 0x1000)
        struct.pack_into('<I', image, opt + 28, 0x400000)
        struct.pack_into('<I', image, opt + 92, 2)
        struct.pack_into('<II', image, opt + 104, 0x1000, 40)
        struct.pack_into('<8sIIIIIIHHI', image, opt + 112, b'.text', 512, 0x1000,
                         512, 0x200, 0, 0, 0, 0, 0x60000000)
        struct.pack_into('<IIIII', image, 0x200, 0x1040, 0, 0, 0x1030, 0x1090)
        image[0x230:0x23d] = b'KERNEL32.dll\0'
        struct.pack_into('<III', image, 0x240, 0x1080, 0x80000007, 0)
        symbol = b'GetCommandLineW\0'
        image[0x282:0x282 + len(symbol)] = symbol

        with tempfile.TemporaryDirectory() as path:
            source, output = Path(path)/'sample.exe', Path(path)/'sample.sbef'
            source.write_bytes(image)
            base = [sys.executable, '-B', sbef.__file__, '--json-errors']
            inventory = json.loads(subprocess.check_output([*base, 'probe', str(source)]))
            self.assertEqual((inventory['SourceFormat'], inventory['Architecture']), ('PE32', 'x86'))
            self.assertEqual(inventory['ImageBase'], 0x400000)
            self.assertEqual(inventory['Imports'], [
                dict(DLL='KERNEL32.dll', Symbols=[dict(Name='GetCommandLineW'), dict(Ordinal=7)])])
            self.assertEqual(inventory['ImportCoverage']['FixtureSymbolCount'], 0)
            self.assertEqual(inventory['Admission']['Imports']['Counts'],
                             dict(available_in_fixture=0, missing=1, ordinal=1))
            report = json.loads(subprocess.check_output([*base, 'catalog', path, '--game', 'Sample Game']))
            self.assertEqual(report['Files'][0]['Format'], 'PE32 x86')
            self.assertEqual(report['Project']['SuggestedDirectory'], 'Game/Sample Game')
            self.assertEqual(report['LaunchCandidates'][0]['Admission'], 'BLOQUEADO')
            self.assertEqual(report['Dependencies'][0]['Symbols'], ['GetCommandLineW', '#7'])
            producer_probe = subprocess.run(
                [*base, 'probe', str(source), '--producer', 'msvc'], capture_output=True)
            self.assertEqual(producer_probe.returncode, 1)
            self.assertEqual(json.loads(producer_probe.stderr)['Code'], 'HOST-PRODUCER-FORMAT')
            result = subprocess.run([*base, 'pack', str(source), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)['Code'], 'PE-MACHINE')
            self.assertFalse(output.exists())

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
            self.assertEqual(inventory['ImportCoverage']['PendingSymbolCount'], 2)
            self.assertEqual(inventory['ImportCoverage']['Libraries'][0]['Group'], 'core')
            result = subprocess.run([*base, 'pack', str(source), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr), expected)
            explained = subprocess.run([*base, 'pack', str(source), str(output), '--explain'], capture_output=True)
            self.assertEqual(explained.returncode, 1)
            details = json.loads(explained.stderr)
            self.assertEqual(details.pop('Admission'), inventory['Admission'])
            self.assertEqual(details, expected)
            markdown = subprocess.check_output([*base, 'probe', str(source), '--format', 'markdown'], text=True)
            self.assertIn('KERNEL32.dll!Sleep', markdown)
            self.assertIn('Ordinal pendiente', markdown)
            self.assertFalse(output.exists())
            directory = source.parent / 'alternate'
            directory.mkdir()
            dll = bytearray(image)
            struct.pack_into('<H', dll, 0x84 + 18, 0x2002)
            first = source.with_name('kernel32.dll')
            first.write_bytes(dll)
            (directory / 'KERNEL32.dll').write_bytes(dll)
            catalog = json.loads(subprocess.check_output([*base, 'catalog', path, '--game', 'Sample Game']))
            self.assertEqual(catalog['Project']['SuggestedDirectory'], 'Game/Sample Game')
            self.assertEqual(catalog['Project']['DependencyFamilies'], ['core'])
            bad_title = subprocess.run([*base, 'catalog', path, '--game', '../Outside'], capture_output=True)
            self.assertEqual(bad_title.returncode, 1)
            self.assertEqual(json.loads(bad_title.stderr)['Code'], 'HOST-CATALOG-TITLE')
            edge = next(edge for edge in catalog['Dependencies'] if edge['From'] == 'app.exe')
            self.assertEqual(edge['Family'], 'core')
            self.assertEqual(edge['Symbols'], ['Sleep', '#7'])
            self.assertEqual(edge['SymbolsWithoutRuntimeEvidence'], ['Sleep', '#7'])
            self.assertEqual(catalog['LaunchCandidates'][0]['DeclaredDLLs'], ['kernel32.dll'])
            self.assertEqual(catalog['LaunchCandidates'][0]['Blockers'], [expected])
            self.assertEqual(edge['Status'], 'AMBIGUA')
            self.assertEqual(edge['LocalCandidates'], ['alternate/KERNEL32.dll', 'kernel32.dll'])
            mismatch = subprocess.run([*base, 'pack', str(source), str(output), '--abi', '1',
                                       '--with-dll', str(first), '--expected-dll-sha256', '0' * 64],
                                      capture_output=True)
            self.assertEqual(mismatch.returncode, 1)
            self.assertEqual(json.loads(mismatch.stderr), dict(Code='HOST-CATALOG-HASH', Field='DLL.file', Offset=0))
            self.assertFalse(output.exists())
            struct.pack_into('<Q', image, 0x240, 0x1200)
            rejected = probe_pe(image)
            self.assertFalse(rejected['CanPack'])
            self.assertEqual(rejected['ImportInventoryError'], dict(
                Code='PE-IMPORT-RVA', Offset=0x240, Field='ImportByName'))
            source.write_bytes(image)
            rejected_cli = json.loads(subprocess.check_output([*base, 'probe', str(source)]))
            self.assertNotIn('ImportCoverage', rejected_cli)
            self.assertEqual(rejected_cli['Admission']['Imports']['Status'], 'invalid')
            self.assertEqual(rejected_cli['Admission']['Imports']['Error']['Code'], 'PE-IMPORT-RVA')

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
