"""Apply the saved Genesis colours and vertical positions, preserving unrelated layout."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply(order, config, reset=False):
    if config.get('schema') != 1 or config.get('direction') != 'houdini':
        raise ValueError('GENESIS-GRAPH-SCHEMA')
    positions = order.setdefault('grafo', {})
    colors = order.setdefault('tintes', {})
    seen = set()
    for node in config['nodes']:
        path, rgb, reason, position = node['path'], node['rgb'], node['reason'], node['position']
        if path in seen or not path or '\\' in path or ':' in path or any(p in {'','.', '..'} for p in path.split('/')):
            raise ValueError('GENESIS-GRAPH-PATH')
        if not (ROOT/path).is_file() or len(rgb) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in rgb) or not reason.strip() or len(reason) > 512:
            raise ValueError('GENESIS-GRAPH-COLOR')
        if len(position) != 2 or any(type(v) is not int or abs(v) > 1000000 for v in position):
            raise ValueError('GENESIS-GRAPH-POSITION')
        seen.add(path)
        if reset or path not in positions: positions[path] = position
        if reset or path not in colors: colors[path] = dict(rgb=rgb, motivo=reason)
    order['direccion'] = 'houdini'
    expanded = set(order.get('desplegadas', []))
    for path in seen:
        expanded.update(p.as_posix() for p in Path(path).parents if p.as_posix() != '.')
    order['desplegadas'] = sorted(expanded); order['foco'] = 'kernel/boot/genesis'
    order['bloqueada'] = True
    if reset or 'kernel/boot/genesis' not in positions: positions['kernel/boot/genesis'] = [0,0]
    for i,name in enumerate(['main.casm','expected.hex','host.json','README.md']):
        path=f'kernel/boot/genesis/{name}'
        if reset or path not in positions: positions[path] = [0,180*(i+1)]
    return order


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset',action='store_true',help='Restore the declared Genesis styles and positions')
    args=parser.parse_args()
    target = ROOT/'super-grafo/orden.json'
    order = json.loads(target.read_text(encoding='utf-8-sig'))
    config = json.loads((ROOT/'super-grafo/genesis.json').read_text())
    # Work on a copy: a rejected configuration must not change the saved layout.
    result = apply(order, config, args.reset)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n',encoding='ascii',newline='\n')
    print('Genesis: posiciones, colores con motivo y direccion Houdini guardados.')
