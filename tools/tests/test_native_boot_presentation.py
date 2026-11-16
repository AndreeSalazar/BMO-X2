"""The quiet desktop variant may change success text/path, never instructions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'boot'))
from stage_bmo_x2 import bridge_variant

class NativePresentation(unittest.TestCase):
    def test_quiet_success_preserves_code_context_and_error_paths(self):
        baseline=bridge_variant();quiet=bridge_variant(native_ui=True)
        self.assertEqual(len(baseline),len(quiet))
        self.assertIn(b'METAL64: BootServices cerrados.',baseline)
        self.assertNotIn(b'METAL64: BootServices cerrados.',quiet)
        self.assertEqual(quiet[0x1b00:0x1c80],bytes(0x180))
        self.assertIn('\\BMO-X2\\DESKTOP\\INICIO.X86'.encode('utf-16le'),quiet)
        changed=[i for i,(a,b) in enumerate(zip(baseline,quiet)) if a!=b]
        self.assertTrue(changed)
        self.assertTrue(all(0x1840<=i<0x1880 or 0x1b00<=i<0x1c80 for i in changed))

if __name__=='__main__':unittest.main()
