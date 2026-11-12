"""Closed privileged profile: source boundary, manual vector and hostile IR/HEX."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'CASM'))
from stop_verify import verify
from verify import verify as legacy_verify


class Stop(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source, self.hex, self.ir = [self.path/name for name in ['source.casm', 'program.hex', 'program.ir.json']]
        self.source.write_bytes((ROOT/'kernel/boot/stop/main.casm').read_bytes())
        self.compiler = ROOT/'build/CASM/host/casmc.exe'

    def compile(self, profile=True):
        args = ['--profile', 'ring0-stop-0.1'] if profile else []
        return subprocess.run([str(self.compiler), *args, str(self.source), str(self.hex), str(self.ir)], capture_output=True)

    def test_source_line_comments_and_manual_vector(self):
        self.source.write_bytes(b'// cpu_halt();\nvoid/*split*/kernel_main(void) {\n/* more\n */ cpu_halt ( ) ; } // end')
        self.assertEqual(self.compile().returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir)
        self.assertEqual(packet[24:], bytes.fromhex((ROOT/'kernel/boot/stop/expected.hex').read_text()))
        self.assertEqual(len(packet), 28)
        self.assertEqual(report['Mapping'][0]['Line'], 4)
        with self.assertRaises(ValueError): legacy_verify(self.source, self.hex, self.ir)

    def test_closed_grammar_both_analyzers(self):
        original = self.source.read_bytes()
        self.assertEqual(self.compile().returncode, 0)
        bad = [original.replace(b'cpu_halt();', value) for value in
               [b'', b'return;', b'cpu_halt(1);', b'cpu_halt(); return;', b'cpu_halt(); cpu_halt();',
                b'metal_puts("x");', b'asm("hlt");', b'const u64 x=1; cpu_halt();']]
        bad += [original+b'void extra(void) {}', original.replace(b'kernel_main', b'metal_main'),
                original+b'/*', original+b'\x00', original+b'\xff', original.replace(b'void ', b'void\v', 1),
                b' '*65537]
        for source in bad:
            with self.subTest(source=source[:100]):
                self.source.write_bytes(source)
                self.assertNotEqual(self.compile().returncode, 0)
                with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.source.write_bytes(original)
        self.assertNotEqual(self.compile(False).returncode, 0)

    def test_all_byte_bits_and_ir_contract_reject(self):
        self.assertEqual(self.compile().returncode, 0)
        vector = bytes.fromhex(self.hex.read_text())
        for index in range(4):
            for bit in range(8):
                mutated = bytearray(vector); mutated[index] ^= 1 << bit
                self.hex.write_text(mutated.hex(' '))
                with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.hex.write_text(vector.hex(' '))
        original = json.loads(self.ir.read_text())
        for key in original:
            mutated = copy.deepcopy(original); del mutated[key]
            self.ir.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        for key, value in [('RequiredCPL', False), ('Schema', 2), ('ABI', 'metal64'),
                           ('Effects', ['halt']), ('Terminal', {'Line': 2, 'Offset': 1}),
                           ('Terminal', {'Line': 1, 'Offset': 0}), ('BodyBytes', 5)]:
            mutated = copy.deepcopy(original); mutated[key] = value
            self.ir.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.ir.write_text(json.dumps(original)[:-1]+',"Schema":3}')
        with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)

    def test_cli_rejection_publishes_nothing(self):
        self.assertEqual(self.compile().returncode, 0)
        self.hex.write_text('FA F4 EB FC')
        packet, report = self.path/'INICIO.X86', self.path/'verified.json'
        result = subprocess.run([sys.executable, '-B', str(ROOT/'CASM/stop_verify.py'),
                                 str(self.source), str(self.hex), str(self.ir), '--packet', str(packet),
                                 '--report', str(report)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(packet.exists()); self.assertFalse(report.exists())


if __name__ == '__main__': unittest.main()
