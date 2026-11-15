"""Verify that graph generation keeps future subsystems out of source folders."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import project


class PlanPages(unittest.TestCase):
    def test_regeneration_writes_a_plan_file_without_a_ghost_source_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = root / 'super-grafo'
            graph.mkdir()
            node = dict(id='future', titulo='Future', ruta='contracts/plans/future.md',
                        estado='diseno', anillo='contrato', lenguaje='contrato',
                        posicion=[0, 0], que='Plan', entrada='Input', salida='Output',
                        aceptacion='Check', falta='Implement', pagina=True,
                        implementacion_prevista=dict(ruta='kernel/future', anillo='0', lenguaje='CASM'))
            data = dict(esquema=1, destino='x86-64', ring0='CASM', ring3='Rust', nodos=[node], relaciones=[])
            with patch.object(project, 'ROOT', root), patch.object(project, 'SG', graph):
                project.generate(data)
                before = (root / node['ruta']).read_bytes()
                project.generate(data)
                self.assertEqual(before, (root / node['ruta']).read_bytes())
                self.assertFalse((root / 'kernel/future').exists())
                node['implementacion_prevista']['ruta'] = '../outside'
                with self.assertRaises(ValueError):
                    project.validate(data, paths=False)

    def test_implemented_directory_pages_keep_working(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = root / 'super-grafo'
            graph.mkdir()
            node = dict(id='real', titulo='Real', ruta='kernel/real', estado='qemu',
                        anillo='0', lenguaje='CASM', posicion=[0, 0], que='Code',
                        entrada='Input', salida='Output', aceptacion='Check', falta='More', pagina=True)
            data = dict(esquema=1, destino='x86-64', ring0='CASM', ring3='Rust', nodos=[node], relaciones=[])
            with patch.object(project, 'ROOT', root), patch.object(project, 'SG', graph):
                project.generate(data)
                self.assertTrue((root / 'kernel/real/README.md').is_file())


if __name__ == '__main__':
    unittest.main()
