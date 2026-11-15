"""Check missing references and provenance handling without deleting files."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import workspace_audit


class AuditChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'heritage').mkdir()
        (self.root / 'super-grafo').mkdir()
        (self.root / 'heritage/casm-origin.json').write_text(json.dumps(dict(origen='ancestor', archivos=[])))
        (self.root / 'heritage/bridge-origin.json').write_text(json.dumps(dict(project='ancestor', files=[])))
        (self.root / 'super-grafo/nodes.json').write_text('{"nodos": []}')

    def report(self, names):
        output = SimpleNamespace(stdout='\0'.join(names).encode())
        with patch.object(workspace_audit, 'ROOT', self.root), patch.object(workspace_audit.subprocess, 'run', return_value=output):
            return workspace_audit.audit()

    def test_missing_files_and_inputs_are_reported_separately(self):
        (self.root / 'source.rs').write_text('const DATA: &[u8] = include_bytes!("absent.bin");')
        report = self.report(['source.rs', 'ghost.rs'])
        self.assertEqual(report['missing_files'], ['ghost.rs'])
        self.assertEqual(report['missing_rust_inputs'][0]['target'], 'absent.bin')
        self.assertEqual(report['errors'], 2)

    def test_document_links_are_checked_but_examples_are_not(self):
        (self.root / 'doc.md').write_text('[bad](missing.md)\n```text\n[example](template.md)\n```\n')
        report = self.report(['doc.md'])
        self.assertEqual(report['broken_local_links'], [dict(source='doc.md', target='missing.md')])

    def test_historical_classification_requires_the_original_hash(self):
        source = self.root / 'import.md'
        source.write_text('[old](old-evidence.md)\n')
        original = dict(ruta='import.md', sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        (self.root / 'heritage/casm-origin.json').write_text(json.dumps(dict(origen='ancestor', archivos=[original])))
        report = self.report(['import.md'])
        self.assertEqual(report['errors'], 0)
        self.assertEqual(len(report['historical_links']), 1)
        source.write_text('[old](old-evidence.md)\nChanged locally.\n')
        self.assertEqual(self.report(['import.md'])['errors'], 1)

    def test_retired_plan_folder_is_flagged_until_it_contains_code(self):
        folder = self.root / 'kernel/future'
        folder.mkdir(parents=True)
        (folder / 'README.md').write_text('Only a plan')
        migration = self.root / 'super-grafo/migrations'
        migration.mkdir()
        (migration / 'plan-folders.json').write_text('{"moves": [{"old": "kernel/future"}]}')
        self.assertEqual(self.report([])['recreated_plan_folders'], ['kernel/future'])
        (folder / 'main.casm').write_text('Actual source')
        self.assertEqual(self.report([])['recreated_plan_folders'], [])


if __name__ == '__main__':
    unittest.main()
