"""Check the exact ULTRA-J vectors and invalid binary cases."""
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
import unittest

from compiler import compile_source
from package import PackageError, build
from runtime import Rejection, run
from view import compile_view


VECTORS = Path(__file__).resolve().parent / 'examples'
PROGRAM = bytes.fromhex((VECTORS / 'window.ujb.hex').read_text(encoding='ascii'))
THEME = bytes.fromhex((VECTORS / 'graphite.ujt.hex').read_text(encoding='ascii'))
SOURCE = (VECTORS / 'WindowDemo.uj').read_bytes()


def image(code):
    return PROGRAM[:6] + len(code).to_bytes(2, 'little') + code


class UltraJTests(unittest.TestCase):
    def test_package_reproduces_panel(self):
        panel = VECTORS / 'panel'
        bytecode, display, graph = build(panel)
        markup = 'view/main.ujh'
        style = 'dependencies/graphite/1/style.ujc'
        self.assertEqual(bytecode, bytes.fromhex('55 4A 42 43 02 00 0A 00 10 01 20 02 40 00 02 30 01 FF'))
        self.assertIn({'From': 'action/main.uj', 'To': 'crates/Activate/main.uj',
                       'Reason': 'Activate.run()', 'Line': 3}, graph)
        self.assertEqual(display, compile_view((panel / markup).read_text(encoding='ascii'),
                                               (panel / style).read_text(encoding='ascii')))
        self.assertIn({'From': markup, 'To': style}, graph)

    def test_package_reports_path_and_required_by(self):
        with TemporaryDirectory() as directory:
            panel = Path(directory) / 'panel'
            copytree(VECTORS / 'panel', panel)
            style = panel / 'dependencies/graphite/1/style.ujc'
            style.unlink()
            with self.assertRaises(PackageError) as caught:
                build(panel)
            report = caught.exception.report
            self.assertEqual(report['Code'], 'PACKAGE_MISSING')
            self.assertEqual(Path(report['Path']), style.resolve())
            self.assertEqual(Path(report['RequiredBy']), (panel / 'view/main.ujh').resolve())
            action = panel / 'action/main.uj'
            action.write_text('class Demo {\n    invalid\n}', encoding='ascii')
            with self.assertRaises(PackageError) as caught:
                build(panel)
            self.assertEqual((caught.exception.report['Line'], caught.exception.report['Column']), (2, 5))

    def test_crate_is_resolved_only_when_called_and_detects_cycles(self):
        with TemporaryDirectory() as directory:
            panel = Path(directory) / 'panel'
            copytree(VECTORS / 'panel', panel)
            spare = panel / 'crates/Spare'
            spare.mkdir()
            (spare / 'main.uj').write_bytes(b'invalid')
            build(panel)
            entry = panel / 'crates/Activate/main.uj'
            entry.write_bytes(b'class Activate { static void run() { Activate.run(); return; } }')
            with self.assertRaises(PackageError) as caught:
                build(panel)
            self.assertEqual(caught.exception.report['Code'], 'CRATE_CYCLE')
            entry.unlink()
            with self.assertRaises(PackageError) as caught:
                build(panel)
            self.assertEqual(caught.exception.report['Code'], 'PACKAGE_MISSING')
            self.assertEqual(Path(caught.exception.report['RequiredBy']),
                             (panel / 'action/main.uj').resolve())

    def test_methods_have_distinct_receivers(self):
        source = (VECTORS / 'ObjectDemo.uj').read_bytes()
        program = compile_source(source)
        self.assertEqual(program, bytes.fromhex(
            '55 4A 42 43 02 00 12 00 10 01 20 01 20 02 40 00 01 40 01 02 40 00 01 30 01 FF'))
        report = run(program, THEME)
        self.assertEqual(report['Calls'], [
            dict(Receiver=0, Method=1, Before=0, After=1),
            dict(Receiver=1, Method=2, Before=0, After=1),
            dict(Receiver=0, Method=1, Before=1, After=1),
        ])
        self.assertEqual(report['LiveObjectBytes'], 0)

    def test_method_guards(self):
        source = (VECTORS / 'ObjectDemo.uj').read_bytes()
        with self.assertRaises(Rejection):
            compile_source(source.replace(b'panel.show()', b'panel.activate()'))
        with self.assertRaises(Rejection):
            compile_source(source.replace(b'        return;', b'        panel.show(); return;'))
        program = compile_source(source)
        for index, value, expected in ((4, 1, 'OPCODE'), (15, 3, 'RECEIVER'), (16, 2, 'METHOD')):
            invalid = bytearray(program)
            invalid[index] = value
            with self.subTest(expected=expected), self.assertRaises(Rejection) as caught:
                run(invalid, THEME)
            self.assertEqual(caught.exception.code, expected)

    def test_source_matches_golden_bytes(self):
        self.assertEqual(compile_source(SOURCE), PROGRAM)
        self.assertEqual(compile_source(b'/* comment */\n' + SOURCE), PROGRAM)
        changed = SOURCE.replace(b'new Button();', b'new Window();', 1)
        self.assertEqual(run(compile_source(changed), THEME)['PeakObjectBytes'], 80)

    def test_source_reports_offsets(self):
        changed = SOURCE.replace(b'Button', b'Unknown', 1)
        with self.assertRaises(Rejection) as caught:
            compile_source(changed)
        self.assertEqual((caught.exception.code, caught.exception.offset),
                         ('SOURCE_CLASS', changed.index(b'Unknown')))

    def test_release_and_reuse(self):
        report = run(PROGRAM, THEME)
        self.assertEqual((len(PROGRAM), len(THEME)), (25, 32))
        self.assertEqual(report['ArenaBytes'], 256)
        self.assertEqual(report['PeakObjectBytes'], 64)
        self.assertEqual(report['LiveObjectBytes'], 0)
        self.assertEqual([a['Offset'] for a in report['Allocations']], [0, 32, 48, 0])
        self.assertEqual(report['Releases'], [
            dict(Region=1, Objects=3, Bytes=64), dict(Region=2, Objects=1, Bytes=32),
        ])

    def test_theme_is_independent(self):
        custom = bytearray(THEME)
        custom[20 + 4:20 + 8] = bytes.fromhex('00 FF 00 00')
        first, second = run(PROGRAM, THEME), run(PROGRAM, custom)
        self.assertEqual(first.pop('Styles')['Button']['Background'], '#5AD8FF')
        self.assertEqual(second.pop('Styles')['Button']['Background'], '#00FF00')
        self.assertEqual(first, second)

    def test_rejects_invalid_program(self):
        cases = [
            (PROGRAM[:-1], 'CODE_SIZE', 6),
            (image(b'\x00'), 'OPCODE', 8),
            (image(b'\x10'), 'MISSING_OPERAND', 9),
            (image(bytes.fromhex('10 00 FF')), 'REGION_OPEN', 9),
            (image(bytes.fromhex('20 01 FF')), 'NO_REGION', 8),
            (image(bytes.fromhex('10 01 20 03 FF')), 'CLASS', 11),
            (image(bytes.fromhex('10 01 30 02 FF')), 'REGION_CLOSE', 11),
            (image(bytes.fromhex('10 01 FF')), 'LIVE_REGION', 10),
            (image(bytes.fromhex('FF FF')), 'AFTER_RETURN', 9),
            (image(bytes.fromhex('10 01 30 01')), 'MISSING_RETURN', 12),
            (image(bytes.fromhex('10 01') + bytes.fromhex('20 01') * 9), 'REGION_CAPACITY', 26),
        ]
        for program, code, offset in cases:
            with self.subTest(code=code), self.assertRaises(Rejection) as caught:
                run(program, THEME)
            self.assertEqual((caught.exception.code, caught.exception.offset), (code, offset))

    def test_rejects_invalid_theme(self):
        for offset, value, code in ((8, 2, 'STYLE_CLASS'), (9, 33, 'STYLE_RADIUS'),
                                    (10, 33, 'STYLE_PADDING'), (11, 1, 'STYLE_RESERVED')):
            theme = bytearray(THEME)
            theme[offset] = value
            with self.subTest(code=code), self.assertRaises(Rejection) as caught:
                run(PROGRAM, theme)
            self.assertEqual((caught.exception.code, caught.exception.offset), (code, offset))


if __name__ == '__main__':
    unittest.main()
