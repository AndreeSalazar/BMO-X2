"""Regression checks for reports of independently verified bytes."""
from pathlib import Path
import shutil
import tempfile
import unittest
from hex_report import ROOT, render


class Report(unittest.TestCase):
    def test_packet_and_hex_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='casm-hex-report-') as folder:
            run = Path(folder)
            source = next(p for p in sorted((ROOT/'build/CASM').glob('run-*'), reverse=True)
                          if (p/'source.casm').is_file() and (p/'source.casm').read_bytes() == (ROOT/'kernel/boot/entry.casm').read_bytes()
                          and (p/'INICIO.X86').is_file())
            for name in ['source.casm', 'program.hex', 'program.ir.json', 'INICIO.X86']:
                shutil.copyfile(source/name, run/name)
            text = render(run)
            self.assertIn('Cuerpo: 48 bytes. Paquete: 72 bytes.', text)
            self.assertIn('| 5 | 0 | 24 | metal_puts |', text)
            packet = (run/'INICIO.X86').read_bytes()
            (run/'INICIO.X86').write_bytes(packet[:-1] + b'X')
            with self.assertRaisesRegex(ValueError, 'PACKET-MISMATCH'):
                render(run)
            (run/'INICIO.X86').write_bytes(packet)
            (run/'program.hex').write_text('90 ' + (run/'program.hex').read_text()[3:])
            with self.assertRaises(ValueError):
                render(run)


if __name__ == '__main__':
    unittest.main()
