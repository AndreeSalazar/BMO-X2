"""Read-only checks for missing files, broken local links and retired plan folders.

No file is considered disposable merely because a text search finds no users.
Build output is outside this audit; historical run paths are not source files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def audit():
    originals = {}
    casm = json.loads((ROOT / 'heritage/casm-origin.json').read_text())
    for entry in casm['archivos']:
        originals[entry['ruta']] = (entry['sha256'], ROOT.parent / casm['origen'] / entry['ruta'])
    bridge = json.loads((ROOT / 'heritage/bridge-origin.json').read_text())
    for entry in bridge['files']:
        originals[entry['path']] = (entry['local_sha256'], ROOT.parent / bridge['project'] / entry['origin'])
    names = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                           cwd=ROOT, capture_output=True, check=True).stdout.decode('utf-8').split('\0')
    missing, links, rust, historical = [], [], [], []
    checked = 0
    for name in sorted(set(filter(None, names))):
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
            continue
        if path.suffix not in ('.md', '.rs'):
            continue
        text = path.read_text(encoding='utf-8-sig')
        if path.suffix == '.md':
            text = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.S)
            for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', text):
                target = target.strip().split(' "', 1)[0].strip('<>')
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                relative = unquote(target.split('#', 1)[0])
                if not relative:
                    continue
                resolved = (path.parent / relative).resolve()
                if not resolved.is_relative_to(ROOT) or relative.replace('\\', '/').startswith('build/'):
                    continue
                checked += 1
                if not resolved.exists():
                    original = originals.get(name)
                    if original and hashlib.sha256(path.read_bytes()).hexdigest() == original[0]:
                        upstream = (original[1].parent / relative).resolve()
                        historical.append(dict(source=name, target=relative,
                                               upstream_available=upstream.exists(),
                                               reason='Unchanged imported document; link belongs to its source project'))
                    else:
                        links.append(dict(source=name, target=relative))
        else:
            targets = re.findall(r'include_(?:bytes|str)!\(\s*"([^"\n]+)"\s*\)', text)
            targets += re.findall(r'#\[path\s*=\s*"([^"\n]+)"\]', text)
            for target in targets:
                checked += 1
                if not (path.parent / target).is_file():
                    rust.append(dict(source=name, target=target))
    data = json.loads((ROOT / 'super-grafo/nodes.json').read_text())
    nodes = [n['ruta'] for n in data['nodos'] if not (ROOT / n['ruta']).exists()]
    retired, retired_documents = [], []
    migration = ROOT / 'super-grafo/migrations/plan-folders.json'
    if migration.exists():
        retired_data = json.loads(migration.read_text())
        for entry in retired_data['moves']:
            old = ROOT / entry['old']
            if old.is_dir() and all(p.name == 'README.md' for p in old.rglob('*') if p.is_file()):
                retired.append(entry['old'])
        retired_documents = [name for name in retired_data.get('retired_plan_documents', [])
                             if (ROOT / name).exists()]
    errors = len(missing) + len(links) + len(rust) + len(nodes) + len(retired) + len(retired_documents)
    return dict(scope='Source paths and explicit references; no deletion or unused-code inference',
                files=len(set(filter(None, names))), checked_references=checked, errors=errors,
                missing_files=missing, broken_local_links=links, missing_rust_inputs=rust,
                missing_node_paths=nodes, recreated_plan_folders=retired,
                recreated_plan_documents=retired_documents,
                historical_links=historical)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2))
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
