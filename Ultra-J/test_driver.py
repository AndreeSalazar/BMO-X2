"""HOST tests for declarative registration. No hardware or driver is started."""
import json
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from driver import check_driver, new_driver, prepare_driver
from package import PackageError


SOURCE = '''class UsbInput {
    void register() {
        Driver.target("x86-64");
        Driver.pci("1022:149C");
        Driver.backend("backend.sbef");
        Driver.memory(65536);
        Driver.mmio(0, 0, 65536);
        Driver.dma(40960);
        Driver.events();
    }
}
'''


def fixture(root, source=SOURCE):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'main.uj').write_text(source, encoding='ascii')
    # Minimal ABI 1 SBEF fixture containing RET. Not an operational driver.
    image = struct.pack('<4sHHHHIQII', b'SBEF', 1, 1, 62, 1, 65, 0x40000000, 0, 0)
    image += struct.pack('<QIIIIQ', 0x40000000, 64, 1, 1, 5, 0) + b'\xc3'
    (root / 'backend.sbef').write_bytes(image)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        fixture(self.root)

    def rejection(self, source, code):
        (self.root / 'main.uj').write_text(source, encoding='ascii')
        with self.assertRaises(PackageError) as caught:
            check_driver(self.root)
        self.assertEqual(caught.exception.report['Code'], code)
        return caught.exception.report

    def test_valid_registration_grants_nothing(self):
        report = check_driver(self.root)
        self.assertTrue(report['HostValidated'])
        self.assertFalse(report['RuntimeReady'])
        self.assertEqual(report['GrantedCapabilities'], [])
        self.assertFalse((self.root / 'build').exists())
        module = report['Modules'][0]
        self.assertEqual(module['Pci'], '1022:149C')
        self.assertEqual(module['StaticMappedBytes'], 4096)
        self.assertTrue(module['RequestedResources'][1]['RequiresIommu'])
        prepared = prepare_driver(self.root)
        self.assertEqual(prepared, json.loads((self.root / 'build/driver-request.json').read_text()))

    def test_dependency_order_is_bounded_and_reports_missing_parent(self):
        fixture(self.root, SOURCE.replace('Driver.events();', 'Driver.events(); Driver.depends("base");'))
        dependency = self.root / 'dependencies/base'
        fixture(dependency)
        self.assertEqual(check_driver(self.root)['StartOrder'], ['dependencies/base/main.uj', 'main.uj'])
        (dependency / 'main.uj').unlink()
        with self.assertRaises(PackageError) as caught:
            check_driver(self.root)
        self.assertEqual(caught.exception.report['Code'], 'PACKAGE_MISSING')
        self.assertEqual(caught.exception.report['RequiredBy'], str(self.root / 'main.uj'))

    def test_cycle_rejected(self):
        source = SOURCE.replace('Driver.events();', 'Driver.events(); Driver.depends("base");')
        fixture(self.root, source)
        fixture(self.root / 'dependencies/base', source)
        with self.assertRaises(PackageError) as caught:
            check_driver(self.root)
        self.assertEqual(caught.exception.report['Code'], 'DRIVER_CYCLE')

    def test_syntax_and_unknown_privileges_are_rejected_with_location(self):
        error = self.rejection(SOURCE.replace('Driver.events();', 'Driver.root();'), 'DRIVER_CALL')
        self.assertEqual(error['Line'], 9)
        self.rejection(SOURCE.replace('Driver.events();', 'while (1) {}'), 'DRIVER_SYNTAX')
        self.rejection(SOURCE + 'Driver.events();', 'DRIVER_SYNTAX')

    def test_identity_and_resources_are_strict(self):
        for old, new, code in [
            ('x86-64', 'power', 'DRIVER_TARGET'),
            ('1022:149C', 'FFFF:FFFF', 'DRIVER_TARGET'),
            ('Driver.memory(65536);', 'Driver.memory(1);', 'DRIVER_MEMORY'),
            ('Driver.mmio(0, 0, 65536);', 'Driver.mmio(6, 0, 65536);', 'DRIVER_MMIO'),
            ('Driver.dma(40960);', 'Driver.dma(1);', 'DRIVER_DMA'),
            ('Driver.events();', 'Driver.events(); Driver.events();', 'DRIVER_DUPLICATE'),
            ('Driver.events();', 'Driver.depends("../escape");', 'DRIVER_DEPENDENCY'),
        ]:
            with self.subTest(code=code):
                self.rejection(SOURCE.replace(old, new), code)

    def test_paths_cannot_escape_the_package(self):
        for backend in ('../backend.sbef', '/backend.sbef', 'C:/backend.sbef', 'a/../../backend.sbef'):
            self.rejection(SOURCE.replace('backend.sbef', backend), 'DRIVER_BACKEND_PATH')

    def test_missing_and_invalid_native_images_are_not_published(self):
        (self.root / 'backend.sbef').unlink()
        with self.assertRaises(PackageError):
            prepare_driver(self.root)
        self.assertFalse((self.root / 'build/driver-request.json').exists())
        (self.root / 'backend.sbef').write_bytes(b'wrong')
        with self.assertRaises(PackageError) as caught:
            prepare_driver(self.root)
        self.assertEqual(caught.exception.report['Code'], 'DRIVER_BACKEND')

    def test_native_abi_permissions_and_memory_floor(self):
        for field, value, code in [(6, 0, 'DRIVER_ABI'), (52, 7, 'DRIVER_BACKEND')]:
            fixture(self.root)
            image = bytearray((self.root / 'backend.sbef').read_bytes())
            struct.pack_into('<H' if field == 6 else '<I', image, field, value)
            (self.root / 'backend.sbef').write_bytes(image)
            with self.assertRaises(PackageError) as caught:
                check_driver(self.root)
            self.assertEqual(caught.exception.report['Code'], code)
        fixture(self.root, SOURCE.replace('65536);', '8192);', 1))
        image = bytearray((self.root / 'backend.sbef').read_bytes())
        struct.pack_into('<I', image, 48, 12288)
        (self.root / 'backend.sbef').write_bytes(image)
        with self.assertRaises(PackageError) as caught:
            check_driver(self.root)
        self.assertEqual(caught.exception.report['Code'], 'DRIVER_MEMORY')

    def test_backend_redirection_is_rejected_before_reading(self):
        original = Path.resolve
        with TemporaryDirectory() as other:
            def resolve(path, *args, **kwargs):
                if path == self.root / 'backend.sbef':
                    return Path(other) / 'backend.sbef'
                return original(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolve):
                with self.assertRaises(PackageError) as caught:
                    check_driver(self.root)
            self.assertEqual(caught.exception.report['Code'], 'PACKAGE_PATH')

    def test_output_redirection_is_rejected(self):
        # Use a real symlink where supported, otherwise the filesystem policy
        # is already covered by package.load and the normal output guard.
        with TemporaryDirectory() as other:
            try:
                (self.root / 'build').symlink_to(Path(other), target_is_directory=True)
            except OSError:
                self.skipTest('Symlink creation unavailable')
            with self.assertRaises(PackageError) as caught:
                prepare_driver(self.root)
            self.assertEqual(caught.exception.report['Code'], 'DRIVER_OUTPUT')
            self.assertFalse((Path(other) / 'driver-request.json').exists())

    def test_output_guard_when_the_build_path_resolves_elsewhere(self):
        original = Path.resolve
        with TemporaryDirectory() as other:
            def resolve(path, *args, **kwargs):
                if path == self.root / 'build':
                    return Path(other)
                return original(path, *args, **kwargs)
            with patch.object(Path, 'resolve', resolve):
                with self.assertRaises(PackageError) as caught:
                    prepare_driver(self.root)
            self.assertEqual(caught.exception.report['Code'], 'DRIVER_OUTPUT')
            self.assertFalse((Path(other) / 'driver-request.json').exists())

    def test_failed_prepare_preserves_last_valid_request_without_granting_access(self):
        prepare_driver(self.root)
        output = self.root / 'build/driver-request.json'
        before = output.read_bytes()
        (self.root / 'backend.sbef').write_bytes(b'invalid replacement')
        with self.assertRaises(PackageError):
            prepare_driver(self.root)
        self.assertEqual(output.read_bytes(), before)
        self.assertFalse(json.loads(before)['RuntimeReady'])

    def test_cli_template_and_prepare(self):
        cli = [sys.executable, '-B', str(Path(__file__).resolve().parent / 'uj.py')]
        subprocess.run([*cli, 'new', 'driver', 'usb_input', '--pci', '1022:149c'],
                       cwd=self.root, capture_output=True, check=True)
        folder = self.root / 'usb_input'
        self.assertEqual([p.name for p in folder.iterdir()], ['main.uj'])
        (folder / 'backend.sbef').write_bytes((self.root / 'backend.sbef').read_bytes())
        result = subprocess.run([*cli, 'driver', 'prepare'], cwd=folder, capture_output=True, check=True)
        self.assertFalse(json.loads(result.stdout)['RuntimeReady'])
        duplicate = subprocess.run([*cli, 'new', 'driver', 'usb_input', '--pci', '1022:149c'],
                                   cwd=self.root, capture_output=True)
        self.assertNotEqual(duplicate.returncode, 0)


if __name__ == '__main__':
    unittest.main()
