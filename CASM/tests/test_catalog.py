"""A catalogue may organize and generate types, but must not silently widen the compiler."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalog


class Catalogue(unittest.TestCase):
    def setUp(self):
        self.data = catalog.read()

    def rejected(self, change, rule):
        value = copy.deepcopy(self.data); change(value)
        with self.assertRaisesRegex(ValueError, rule):
            catalog.render_types(value)

    def test_valid_hierarchy_produces_only_the_eight_active_types(self):
        rendered = catalog.render_types(self.data)
        self.assertEqual(rendered.encode(), (catalog.HERE/'src/model/types.c').read_bytes())
        self.assertEqual(rendered.count('{"'), 8)

    def test_unknown_architecture_cannot_generate(self):
        self.rejected(lambda d: d.update(architecture='arm64'), 'CATALOG-TARGET')

    def test_hierarchy_cycles_and_unknown_parents_cannot_generate(self):
        self.rejected(lambda d: d['nodes'][1].update(parent=d['nodes'][1]['id']), 'CATALOG-HIERARCHY')
        self.rejected(lambda d: d['nodes'][1].update(parent='absent'), 'CATALOG-HIERARCHY')

    def test_source_path_cannot_escape(self):
        self.rejected(lambda d: d['nodes'][1].update(sources=['../outside.c']), 'CATALOG-PATH')

    def test_type_disagrees_with_independent_verifier(self):
        def change(d): next(n for n in d['nodes'] if n['kind']=='type').update(bits=64)
        self.rejected(change, 'CATALOG-TYPE')

    def test_encoding_disagrees_with_independent_manual_vector(self):
        def change(d): next(n for n in d['nodes'] if n['id']=='call-r15-service').update(hex='41 FF 57 20')
        self.rejected(change, 'CATALOG-VECTOR')

    def test_unknown_opcode_cannot_be_added_as_implemented(self):
        def change(d):
            n=copy.deepcopy(next(n for n in d['nodes'] if n['id']=='ret'))
            n.update(id='unknown-opcode',hex='90');d['nodes'].append(n)
        self.rejected(change,'CATALOG-ENCODINGS')

    def test_planned_phase_cannot_become_active_pipeline(self):
        def change(d): next(n for n in d['nodes'] if n['id']=='encoding').update(status='planned')
        self.rejected(change,'CATALOG-PIPELINE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
