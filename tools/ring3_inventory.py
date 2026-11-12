"""Inventory the parent Cargo manifests from a pinned Git tree."""
import argparse
from collections import Counter
from pathlib import Path
import subprocess
import tomllib


REVISION = '6076bdefefc67877419ca53633c6e40cb45fc92d'
ROOTS = {
    'Ultra_userspace/apps': 'Aplicacion',
    'Ultra_userspace/services': 'Servicio',
    'Ultra_userspace/userland': 'Runtime',
    'Ultra_userspace/medida': 'Medicion',
    'platform/abi': 'ABI y admision',
    'platform/services': 'Servicio',
    'platform/shared': 'Biblioteca compartida',
    'toolchain/lang/base': 'Runtime',
    'toolchain/tools': 'Toolchain',
}
ABI_NAMES = {'bmo-abi', 'bmo-bex-gate', 'bmo-rt', 'bmo-userland'}


def manifest_dependencies(manifest):
    tables = [manifest, *manifest.get('target', {}).values()]
    return sorted({details.get('package', name) if isinstance(details, dict) else name
                   for table in tables for field in ('dependencies', 'build-dependencies')
                   for name, details in table.get(field, {}).items()})


def render(parent):
    command = ['git', '-c', f'safe.directory={parent.as_posix()}', '-C', str(parent)]
    paths = subprocess.check_output([*command, 'ls-tree', '-r', '--name-only', REVISION, '--', *ROOTS],
                                    text=True, encoding='utf-8').splitlines()
    rows = []
    for path in paths:
        if not path.endswith('/Cargo.toml'):
            continue
        manifest = tomllib.loads(subprocess.check_output(
            [*command, 'show', f'{REVISION}:{path}'], text=True, encoding='utf-8'))
        package = manifest.get('package')
        if not package:
            continue
        family = next(label for prefix, label in ROOTS.items() if path.startswith(prefix + '/'))
        dependencies = manifest_dependencies(manifest)
        abi = sorted(ABI_NAMES.intersection(dependencies))
        rows.append((family, package['name'], path.removesuffix('/Cargo.toml'), dependencies, abi))
    if not rows:
        raise ValueError('El arbol del padre no contiene los crates esperados')
    counts = Counter(family for family, *_ in rows)
    lines = [
        '# Inventario de crates para la transferencia',
        '',
        f'BMO-X en `{REVISION}`. Total de paquetes Cargo: **{len(rows)}**.',
        ', '.join(f'{family} ({count})' for family, count in sorted(counts.items())) + '.',
        '',
        'La familia indica el lugar de origen y el orden de revision. El inventario',
        'recoge dependencias declaradas de compilacion normal, build y target.',
        'La columna ABI marca dependencias directas conocidas. Para admitir un',
        'crate se requieren su cierre transitivo, un build para BMO-X2 y una',
        'prueba de las capacidades del componente. Todos quedan por validar.',
        '',
        '| Familia | Crate | Ruta en BMO-X | Dependencias directas | ABI directo |',
        '|---|---|---|---|---|',
    ]
    for family, name, path, dependencies, abi in sorted(rows):
        lines.append(f"| {family} | `{name}` | `{path}` | {', '.join(dependencies) or '-'} | {', '.join(abi) or '-'} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    inventory = render(args.parent.resolve())
    if args.output:
        args.output.write_text(inventory, encoding='utf-8', newline='\n')
    else:
        print(inventory, end='')


if __name__ == '__main__':
    main()
