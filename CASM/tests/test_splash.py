"""Check the logo format and separate renderer and mask rejection paths."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'CASM'))
from splash_verify import ASSETS, HD_PROFILE, PROFILE, verify


class Splash(unittest.TestCase):
    def test_hd_has_distinct_mask_layout_and_uses_bridge_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            source, hexa, ir = [run/name for name in ('source.casm','program.hex','program.ir.json')]
            source.write_bytes((ASSETS/'hd/main.casm').read_bytes())
            compiler = ROOT/'build/CASM/host/casmc.exe'
            subprocess.run([str(compiler),'--profile',HD_PROFILE,str(source),str(hexa),str(ir)],
                           check=True,capture_output=True)
            packet, report = verify(source,hexa,ir,hd=True)
            self.assertEqual((len(packet),report['Mapping'][-1]['Bytes']),(1279,1024))
            self.assertEqual(report['BridgePacketLimitBytes'],4096)
            self.assertNotIn('EntryBudget',report)
            with self.assertRaises(ValueError):
                verify(source,hexa,ir)
            body = bytearray(bytes.fromhex(hexa.read_text()))
            body[-1] ^= 0x80
            hexa.write_text(body.hex(' '),encoding='ascii')
            with self.assertRaisesRegex(ValueError,'SPLASH-MASK'):
                verify(source,hexa,ir,hd=True)

    def test_emission_and_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            source, hexa, ir = [run/name for name in ('source.casm','program.hex','program.ir.json')]
            source.write_bytes((ASSETS/'main.casm').read_bytes())
            command = [str(ROOT/'build/CASM/host/casmc.exe'), '--profile', PROFILE,
                       str(source), str(hexa), str(ir)]
            subprocess.run(command, check=True, capture_output=True)
            packet, report = verify(source, hexa, ir)
            self.assertEqual(len(packet),508)
            self.assertEqual(report['EntryBudget']['RemainingBytes'],3)
            body = bytes.fromhex(hexa.read_text())
            for offset, reason in [(3,'SPLASH-RENDERER'),(240,'SPLASH-MASK')]:
                mutated = bytearray(body)
                mutated[offset] ^= 1
                hexa.write_text(mutated.hex(' '),encoding='ascii')
                with self.assertRaisesRegex(ValueError, reason):
                    verify(source,hexa,ir)
            hexa.write_text(body.hex(' '),encoding='ascii')
            source.write_text(source.read_text().replace('"............##', '"...........##', 1),encoding='ascii')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            with self.assertRaisesRegex(ValueError, 'SPLASH-SOURCE'):
                verify(source,hexa,ir)


if __name__ == '__main__':
    unittest.main()
