"""Genesis must preserve its manual vector and reject altered inputs."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from genesis import ROOT, check, budget
from genesis_graph import apply


class Genesis(unittest.TestCase):
    def test_strict_packet_budget_includes_the_header(self):
        budget(487,511)
        for body,packet in [(488,512),(512,536),(0,24),(22,45)]:
            with self.assertRaisesRegex(ValueError,'GENESIS-BUDGET'): budget(body,packet)

    def test_exact_source_vector_and_packet(self):
        source = ROOT/'kernel/boot/genesis/main.casm'
        origin = next(p for p in sorted((ROOT/'build/CASM').glob('run-*'),reverse=True)
                      if (p/'INICIO.X86').is_file() and (p/'source.casm').read_bytes() == source.read_bytes())
        with tempfile.TemporaryDirectory(prefix='genesis-') as folder:
            run = Path(folder)
            for name in ['source.casm','program.hex','program.ir.json','INICIO.X86']:
                shutil.copyfile(origin/name,run/name)
            result = check(run)
            self.assertEqual((result['body_bytes'],result['packet_bytes']),(22,46))
            packet = (run/'INICIO.X86').read_bytes()
            (run/'INICIO.X86').write_bytes(packet[:-1]+b'X')
            with self.assertRaisesRegex(ValueError,'GENESIS-PACKET'): check(run)
            (run/'INICIO.X86').write_bytes(packet)
            (run/'source.casm').write_bytes(source.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'GENESIS-SOURCE'): check(run)
            (run/'source.casm').write_bytes(source.read_bytes())
            (run/'program.hex').write_text('90 ' + (run/'program.hex').read_text()[3:])
            with self.assertRaises(ValueError): check(run)

    def test_graph_preserves_unrelated_layout_and_rejects_escape(self):
        config = json.loads((ROOT/'super-grafo/genesis.json').read_text())
        order = {'grafo':{'mine':[100,200]},'tintes':{'mine':{'rgb':[1,2,3],'motivo':'Mi nota'}}}
        result = apply(copy.deepcopy(order),config)
        self.assertEqual(result['grafo']['mine'],[100,200])
        self.assertEqual(result['tintes']['mine'],order['tintes']['mine'])
        self.assertEqual(result['direccion'],'houdini')
        self.assertTrue(result['bloqueada'])
        path=config['nodes'][0]['path'];result['tintes'][path]['rgb']=[7,8,9];result['grafo'][path]=[42,43]
        saved=apply(copy.deepcopy(result),config)
        self.assertEqual(saved['tintes'][path]['rgb'],[7,8,9]);self.assertEqual(saved['grafo'][path],[42,43])
        restored=apply(copy.deepcopy(result),config,reset=True)
        self.assertEqual(restored['tintes'][path]['rgb'],config['nodes'][0]['rgb'])
        bad=copy.deepcopy(config);bad['nodes'][0]['path']='../outside'
        with self.assertRaises(ValueError): apply(copy.deepcopy(order),bad)
        bad=copy.deepcopy(config);bad['nodes'][0]['rgb']=[256,0,0]
        with self.assertRaises(ValueError): apply(copy.deepcopy(order),bad)


if __name__ == '__main__': unittest.main()
