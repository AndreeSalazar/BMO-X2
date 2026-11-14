"""Catalogo de BMO-X2: contratos de nodos y disposicion soportada por SUPER GRAFO."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT / 'super-grafo'
STATES = {'heredado', 'host', 'qemu', 'diseno', 'investigacion'}
KINDS = {'codigo', 'generacion', 'verificacion', 'plan'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def within(relative):
    require(isinstance(relative, str) and relative and '\\' not in relative,
            'Ruta relativa requerida')
    path = Path(relative)
    require(not path.is_absolute() and all(p not in {'.', '..'} for p in relative.split('/')),
            f'Ruta fuera del proyecto: {relative}')
    resolved = (ROOT / path).resolve()
    require(resolved.is_relative_to(ROOT), f'Ruta fuera del proyecto: {relative}')
    return resolved


def validate(data, paths=True):
    require(data.get('esquema') == 1, 'Esquema de nodos desconocido')
    require(data.get('destino') == 'x86-64', 'El destino debe ser x86-64')
    require(data.get('ring0') == 'CASM' and data.get('ring3') == 'Rust', 'Frontera CASM/Rust invalida')
    nodes, edges = data['nodos'], data['relaciones']
    require(isinstance(nodes, list) and 0 < len(nodes) <= 256, 'Cantidad de nodos fuera de limite')
    require(isinstance(edges, list) and len(edges) <= 512, 'Cantidad de relaciones fuera de limite')
    ids, routes, locations = {}, set(), set()
    for n in nodes:
        require(n['id'] not in ids, f"ID repetido: {n['id']}")
        require(n['ruta'] not in routes, f"Ruta repetida: {n['ruta']}")
        ids[n['id']] = n['anillo']; routes.add(n['ruta'])
        path = within(n['ruta'])
        if paths:
            require(path.exists(), f"Nodo sin ruta real: {n['ruta']}")
        require(n['estado'] in STATES, f"Estado desconocido: {n['id']}")
        require(n['anillo'] in {'host', '0', '3', 'contrato'}, f"Anillo desconocido: {n['id']}")
        if n['anillo'] == '0':
            require(n['lenguaje'] == 'CASM', f"Ring 0 requiere CASM: {n['id']}")
            require(n['ruta'].startswith('kernel/'), f"Ring 0 vive en kernel/: {n['id']}")
        if n['anillo'] == '3':
            require(n['lenguaje'] == 'Rust', f"Ring 3 requiere Rust: {n['id']}")
            require(n['ruta'].startswith('userspace/'), f"Ring 3 vive en userspace/: {n['id']}")
        for field in ('que', 'entrada', 'salida', 'aceptacion', 'falta'):
            require(isinstance(n[field], str) and n[field].strip(), f"Falta {field}: {n['id']}")
        position = tuple(n['posicion'])
        require(len(position) == 2 and all(isinstance(x, (int, float)) and math.isfinite(x) and abs(x) <= 1000000 for x in position),
                f"Posicion invalida: {n['id']}")
        require(position not in locations, f"Posicion repetida: {n['id']}")
        locations.add(position)
    graph = {key: [] for key in ids}
    pairs = set()
    for edge in edges:
        require(edge['de'] in ids and edge['a'] in ids, 'Relacion a nodo inexistente')
        require(edge['clase'] in KINDS, 'Clase de relacion desconocida')
        require(edge['de'] != edge['a'], 'Dependencia de si mismo')
        if ids[edge['de']] == '0' and edge['clase'] == 'codigo':
            require(ids[edge['a']] in {'0', 'contrato'},
                    f"Codigo de Ring 0 depende de HOST o Ring 3: {edge['de']} -> {edge['a']}")
        key = (edge['de'], edge['a'], edge['clase'])
        require(key not in pairs, 'Relacion repetida')
        pairs.add(key); graph[edge['de']].append(edge['a'])
    seen, active = set(), set()

    def visit(key):
        require(key not in active, f'Ciclo en contratos de nodos: {key}')
        if key in seen:
            return
        active.add(key)
        for dependency in graph[key]:
            visit(dependency)
        active.remove(key); seen.add(key)

    for key in graph:
        visit(key)
    return nodes, edges


def inherited():
    origin = read(ROOT / 'heritage/casm-origin.json')
    changed = []
    for entry in origin['archivos']:
        actual = hashlib.sha256(within(entry['ruta']).read_bytes()).hexdigest()
        if actual != entry['sha256']:
            changed.append(entry['ruta'])
    adaptations = read(ROOT / 'heritage/casm-changes.json')
    expected = {entry['path'] for entry in adaptations['changes']}
    require(set(changed) == expected, f'Divergencias no registradas de CASM: {changed}')
    return {'archivos': len(origin['archivos']), 'adaptados': changed, 'commit': origin['commit']}


def kernel_profile():
    profile = read(ROOT / 'CASM/x86_64/requirements.json')
    require(profile.get('schema') == 1 and profile.get('architecture') == 'x86-64',
            'Perfil de kernel exclusivo x86-64 requerido')
    features = profile['features']
    require(0 < len(features) <= 64, 'Cantidad de requisitos fuera de limite')
    ids = set()
    counts = {'inherited': 0, 'partial': 0, 'required': 0}
    for feature in features:
        require(feature['id'] not in ids, 'Requisito de kernel repetido')
        ids.add(feature['id'])
        require(feature['status'] in counts, 'Estado de requisito desconocido')
        require(feature['need'] and feature['evidence'], 'Requisito sin motivo o evidencia')
        counts[feature['status']] += 1
    # Inventario de necesidades; no acredita que CASM ya implemente el perfil.
    return {'architecture': profile['architecture'], 'features': len(features), 'status': counts}


def rejection_tests(data):
    bad_cases = []
    mutation = copy.deepcopy(data); mutation['destino'] = 'aarch64'; bad_cases.append(mutation)
    mutation = copy.deepcopy(data); mutation['nodos'][0]['ruta'] = '../BMO/README.md'; bad_cases.append(mutation)
    mutation = copy.deepcopy(data); mutation['nodos'][0]['estado'] = 'terminado'; bad_cases.append(mutation)
    mutation = copy.deepcopy(data); mutation['relaciones'][0]['a'] = 'no-existe'; bad_cases.append(mutation)
    mutation = copy.deepcopy(data); mutation['nodos'][0]['anillo'] = '0'; mutation['nodos'][0]['lenguaje'] = 'Rust'; bad_cases.append(mutation)
    mutation = copy.deepcopy(data)
    next(n for n in mutation['nodos'] if n['id'] == 'rust-services')['ruta'] = 'tools/host'
    bad_cases.append(mutation)
    for target in ('rust-runtime', 'sbef-host-pack'):
        mutation = copy.deepcopy(data)
        mutation['relaciones'].append({'de': 'sbef-loader', 'a': target, 'clase': 'codigo'})
        bad_cases.append(mutation)
    mutation = copy.deepcopy(data)
    edge = mutation['relaciones'][0]
    mutation['relaciones'].append({'de': edge['a'], 'a': edge['de'], 'clase': 'plan'})
    bad_cases.append(mutation)
    for index, mutation in enumerate(bad_cases):
        try:
            validate(mutation)
        except ValueError:
            continue
        raise ValueError(f'El guardian de nodos acepto la mutacion {index}')
    return len(bad_cases)


def generate(data):
    # La ruta de cada futuro subsistema contiene una pagina de contrato, no codigo ficticio.
    for n in data['nodos']:
        if n.get('pagina'):
            directory = within(n['ruta'])
            directory.mkdir(parents=True, exist_ok=True)
            text = (f"# {n['titulo']}\n\n> Generado desde super-grafo/nodes.json.\n\n"
                    f"Estado: {n['estado'].upper()}. Anillo: {n['anillo']}. Lenguaje previsto: {n['lenguaje']}.\n\n"
                    f"{n['que']}\n\n## Contrato del nodo\n\n"
                    f"- Entrada: {n['entrada']}\n- Salida: {n['salida']}\n"
                    f"- Aceptacion: {n['aceptacion']}\n- Pendiente: {n['falta']}\n")
            (directory / 'README.md').write_text(text, encoding='utf-8', newline='\n')
    nodes, edges = validate(data)
    notes = ['# Notas de BMO-X2', '', '> Generadas desde nodes.json; HEREDADO y DISENO no significan ejecutado aqui.', '']
    catalog = ['# Catalogo de nodos de BMO-X2', '', '> Generado desde nodes.json. Relaciones de plan separadas del codigo.', '',
               '| Nodo | Estado | Anillo | Responsabilidad |', '|---|---|---|---|']
    by_id = {n['id']: n for n in nodes}
    for n in nodes:
        dependencies = [f"{by_id[e['a']]['titulo']} ({e['clase']})" for e in edges if e['de'] == n['id']]
        notes.extend([f"## {n['ruta']}", '', n['que'], '', f"Estado: {n['estado'].upper()}. Anillo: {n['anillo']}. Lenguaje: {n['lenguaje']}.",
                      f"Entrada: {n['entrada']}", f"Salida: {n['salida']}",
                      f"Depende de: {', '.join(dependencies) or 'contrato propio sin dependencias en este catalogo'}.",
                      f"Aceptacion: {n['aceptacion']}", f"Pendiente: {n['falta']}", ''])
        catalog.append(f"| [{n['titulo']}](../{n['ruta']}) | {n['estado']} | {n['anillo']} | {n['que']} |")
    catalog.extend(['', '## Dependencias declaradas', '', '| Quien usa | De quien depende | Clase |', '|---|---|---|'])
    for e in edges:
        catalog.append(f"| {e['de']} | {e['a']} | {e['clase']} |")
    catalog.extend(['', 'El grafo de codigo de SG se calcula desde sus fuentes. Estas relaciones tambien incluyen el plan y no se presentan como llamadas ejecutadas.', ''])
    notes.extend([
        '## CASM', '', 'Lenguaje y codificador propio x86-64: metal64, Native y su futura ampliacion privilegiada.',
        '', 'Estado: base HEREDADA; banco metal64 HOST. Ver STATUS-BMO-X2.md para los perfiles y limites.', '',
        '## kernel', '', 'Futuro Ring 0 en CASM: arranque, CPU, excepciones, memoria, capacidades y puerta.',
        '', 'Estado: subsistemas en DISENO; boot/entry.casm es una sonda HOST, aun sin kernel arrancable.', '',
        '## userspace', '', 'Futuro Ring 3 en Rust: runtime minimo, servicios y aplicaciones.',
        '', 'Estado: DISENO; aun sin crates y sin std del anfitrion.', '',
        '## super-grafo', '', 'Mesa de trabajo: catalogo, notas, posiciones y fotografia real del analizador.',
        '', f'{len(nodes)} nodos del catalogo; relaciones de codigo y de plan distinguidas por clase.', ''
    ])
    (SG / 'NOTAS.md').write_text('\n'.join(notes), encoding='utf-8', newline='\n')
    (SG / 'CATALOG.md').write_text('\n'.join(catalog), encoding='utf-8', newline='\n')


def arrange(data):
    nodes, _ = validate(data)
    target = SG / 'orden.json'
    require(target.is_file(), 'Primero ejecutar guardar en SUPER GRAFO')
    order = read(target)
    positions = order.setdefault('grafo', {})
    positions.update({n['ruta']: n['posicion'] for n in nodes})
    # Conservar posiciones de detalle, pero empezar por familias legibles y cerradas.
    # La primera revision visual mostro que desplegar todas las fuentes a la vez
    # hacia ilegibles los nombres al encuadrar. El usuario entra a cada familia.
    expanded = set()
    parents = set()
    for n in nodes:
        path = Path(n['ruta'])
        for parent in path.parents:
            rel = parent.as_posix()
            if rel != '.':
                parents.add(rel)
    # Eliminar posiciones antiguas de rutas renombradas o retiradas.
    positions = {route: pos for route, pos in positions.items() if not route or (ROOT / route).exists()}
    order['grafo'] = positions
    # Padres en filas propias: no se superponen con los nodos del pipeline.
    parents = sorted(parents - {n['ruta'] for n in nodes})
    for i, parent in enumerate(parents):
        positions[parent] = [-680.0, i * 135.0]
    initial = ['CASM', 'kernel', 'userspace', 'contracts', 'tools', 'heritage',
               'docs', 'super-grafo', 'README.md', 'bmo-x2.ps1', 'AGENTS.md']
    for i, route in enumerate(initial):
        positions[route] = [(i % 3) * 320.0, (i // 3) * 165.0]
    positions[''] = [-350.0, 170.0]
    order['desplegadas'] = sorted(expanded)
    order['foco'] = ''
    target.write_text(json.dumps(order, ensure_ascii=True, indent=2) + '\n', encoding='utf-8', newline='\n')
    return len(positions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=['generar', 'comprobar', 'ordenar'])
    args = parser.parse_args()
    data = read(SG / 'nodes.json')
    if args.accion == 'generar':
        validate(data, paths=False)
        generate(data)
    nodes, edges = validate(data)
    result = {'destino': data['destino'], 'nodos': len(nodes), 'relaciones': len(edges), 'heritage': inherited(),
              'pruebas_rechazo': rejection_tests(data), 'kernel_profile': kernel_profile(), 'kernel_arrancable': False}
    if args.accion == 'ordenar':
        result['posiciones_guardadas'] = arrange(data)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f'RED [PROYECTO] {error}') from error
