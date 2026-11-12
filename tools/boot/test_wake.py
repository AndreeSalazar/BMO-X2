"""Host checks for bootstrap conversion and VM output confinement."""
from pathlib import Path
import tempfile
import unittest
from wake import assemble, ROOT
from scope import workspace
from cpu_config import identify


class Wake(unittest.TestCase):
    def test_cpu_profile_uses_observed_register_order_and_rejects_invalid_values(self):
        snapshot = 'RAX=00000001 RBX=68747541 RCX=444D4163 RDX=69746E65'
        self.assertEqual(identify(snapshot), dict(Vendor='AuthenticAMD', MaxBasicLeaf=1))
        for invalid in (snapshot.replace('RDX', 'R8'), snapshot + ' RAX=01',
                        snapshot.replace('68747541', '00647541'),
                        snapshot.replace('00000001', '100000001')):
            with self.assertRaisesRegex(ValueError, 'CPU-CONFIG'):
                identify(invalid)

    def test_bridge_is_exactly_the_imported_hex(self):
        files=[ROOT/'kernel/boot/bridge'/n for n in ['cabecera.hex','entrada.hex','datos.hex','fuente.hex']]
        image=assemble(files)
        self.assertEqual(len(image),12288)
        self.assertEqual(image[0xc90:0xc94],bytes.fromhex('48 8B 55 58'))
        # Independent recorded bridge built by TALK-CPU and observed in first G1.
        import hashlib
        self.assertEqual(hashlib.sha256(image).hexdigest(),'4287ad788cb7a75a74922f7f73e69363560c84501b9a73ba271d357f5f71469f')

    def test_bad_hex_offsets_and_tokens_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='casm-bridge-') as folder:
            file=Path(folder)/'bad.hex'
            for text in ['FF @0','FF =0','@100001','XYZ']:
                file.write_text(text,encoding='ascii')
                with self.assertRaises(ValueError): assemble([file])

    def test_output_requires_a_run_inside_the_project(self):
        for path in [ROOT,ROOT/'build',Path('C:/Windows'),ROOT/'build/CASM/no-run']:
            with self.assertRaises(ValueError): workspace(path)


if __name__=='__main__': unittest.main()
