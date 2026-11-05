"""Validate CASM's bounded x86-64 hierarchy and generate the compiler type table."""
import argparse
import json
from pathlib import Path
import re

from verify import INT_TYPES  # independently authored verifier table, never generated here

HERE = Path(__file__).resolve().parent
CATALOG = HERE / 'catalog.json'
TYPE_ORDER = ['uint8_t', 'uint16_t', 'uint32_t', 'uint64_t', 'int8_t', 'int16_t', 'int32_t', 'int64_t']
KINDS = {'group', 'phase', 'type', 'syntax', 'ir', 'encoding', 'artifact', 'capability', 'profile'}


def require(ok, rule):
    if not ok:
        raise ValueError(rule)


def read():
    raw = CATALOG.read_bytes()
    require(len(raw) <= 262144, 'CATALOG-SIZE')
    return json.loads(raw)


def validate(data):
    require(isinstance(data, dict) and set(data) == {'schema','architecture','profile','pipeline','nodes'}, 'CATALOG-SCHEMA')
    require(data.get('schema') == 1 and data.get('architecture') == 'x86-64', 'CATALOG-TARGET')
    require(data.get('profile') == 'metal64-0.2', 'CATALOG-PROFILE')
    nodes = data['nodes']
    require(isinstance(nodes, list) and 0 < len(nodes) <= 256, 'CATALOG-LIMIT')
    ids = {}
    for node in nodes:
        require(set(node) <= {'id','parent','kind','title','status','description','sources','guards','tests','name','bits','signed','hex','length','fixup','fields'}, 'CATALOG-FIELD')
        if 'fields' in node:
            require(isinstance(node['fields'], list) and len(node['fields']) <= 16 and all(isinstance(v,str) and len(v)<=128 for v in node['fields']), 'CATALOG-FIELDS')
        key = node['id']
        require(isinstance(key, str) and re.fullmatch('[a-z][a-z0-9-]{0,63}', key), 'CATALOG-ID')
        require(key not in ids, 'CATALOG-DUPLICATE')
        require(node['kind'] in KINDS and node['status'] in {'implemented', 'partial', 'planned'}, 'CATALOG-STATE')
        require(node['title'] and node['description'] and len(node['description']) <= 2048, 'CATALOG-TEXT')
        for field in ('sources', 'guards', 'tests'):
            require(isinstance(node[field], list) and len(node[field]) <= 16 and all(isinstance(v,str) and len(v)<=512 for v in node[field]), 'CATALOG-LIST')
        for source in node['sources']:
            require(isinstance(source, str) and '\\' not in source and ':' not in source and
                    not source.startswith('/') and all(p not in {'', '.', '..'} for p in source.split('/')), 'CATALOG-PATH')
            path = HERE / source
            require(path.resolve().is_relative_to(HERE) and path.is_file(), 'CATALOG-SOURCE')
        ids[key] = node
    require([n['id'] for n in nodes if n.get('parent') is None] == ['casm'], 'CATALOG-ROOT')
    for node in nodes:
        seen = set(); current = node
        while current.get('parent') is not None:
            parent = current['parent']
            require(parent in ids and parent not in seen and len(seen) < 8, 'CATALOG-HIERARCHY')
            seen.add(parent); current = ids[parent]
        require(current['id'] == 'casm', 'CATALOG-ROOT')
    require(data['pipeline'] == ['source','frontend','ir','encoding','hex','verification','packet'], 'CATALOG-PIPELINE')
    require(all(key in ids and ids[key]['status'] == 'implemented' for key in data['pipeline']), 'CATALOG-PIPELINE')
    types = [n for n in nodes if n['kind'] == 'type' and n['status'] == 'implemented']
    require([n['name'] for n in types] == TYPE_ORDER, 'CATALOG-TYPES')
    for node in types:
        require(type(node['bits']) is int and type(node['signed']) is bool and
                INT_TYPES[node['name']] == (node['bits'], node['signed']), 'CATALOG-TYPE')
    # Independent, hand-authored vector for the first entry, not data from this catalogue.
    fixture = bytes.fromhex((HERE.parent/'kernel/boot/fixtures/entry.hex').read_text())
    offsets = {'lea-rsi-rip32': (0, 7), 'call-r15-service': (7, 4), 'ret': (11, 1)}
    encodings = [n for n in nodes if n['kind'] == 'encoding' and n['status'] == 'implemented']
    require({n['id'] for n in encodings} == set(offsets), 'CATALOG-ENCODINGS')
    for node in encodings:
        offset, size = offsets[node['id']]; tokens = node['hex'].split()
        require(type(node['length']) is int and node['length'] == size and len(tokens) == size, 'CATALOG-ENCODING')
        for i, token in enumerate(tokens):
            require(token == '??' or bool(re.fullmatch('[0-9A-F]{2}', token)), 'CATALOG-HEX')
            require(token != '??' or (node['id'] == 'lea-rsi-rip32' and 3 <= i < 7), 'CATALOG-FIXUP')
            require(token == '??' or int(token, 16) == fixture[offset+i], 'CATALOG-VECTOR')
    return nodes


def render_types(data):
    nodes = validate(data)
    rows = [n for n in nodes if n['kind'] == 'type' and n['status'] == 'implemented']
    return ('/* Generated from CASM/catalog.json by catalog.py; verifier stays independent. */\n'
            '#include "../casm.h"\n\nconst CasmIntType casm_int_types[8] = {\n' +
            ''.join(f'    {{"{n["name"]}", {n["bits"]}, {int(n["signed"])}}},\n' for n in rows) + '};\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'generate'], default='check', nargs='?')
    args = parser.parse_args()
    data = read(); text = render_types(data)
    target = HERE/'src/model/types.c'
    if args.action == 'generate':
        target.write_text(text, encoding='ascii', newline='\n')
    else:
        require(target.read_bytes() == text.encode('ascii'), 'CATALOG-GENERATED-TYPES-STALE')
    print(json.dumps({'architecture': data['architecture'], 'profile': data['profile'], 'nodes': len(data['nodes']),
                      'types': 8, 'encodings': 3, 'independent_vector_checked': True, 'action': args.action}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit(f'RED [CATALOG] {error}') from error
