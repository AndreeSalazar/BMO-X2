"""Resolve and build an ULTRA-J panel from its folder structure."""
import argparse
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from compiler import MAX_SOURCE, compile_source, publish
from runtime import Rejection, read_bounded
from view import compile_view_rules, stylesheet

PROJECT = Path(__file__).resolve().parent.parent

class PackageError(ValueError):
    def __init__(self, code, path, message, **details):
        self.report = dict(Code=code, Path=str(path), Message=message, **details)


def load(path, root, limit):
    if not path.resolve().is_relative_to(root) or path.resolve() != path:
        raise PackageError('PACKAGE_PATH', path, 'La entrada debe permanecer en su ruta dentro del paquete.')
    if not path.is_file():
        raise PackageError('PACKAGE_MISSING', path, 'Falta el archivo requerido por su carpeta.')
    try:
        return read_bounded(path, limit)
    except (OSError, Rejection) as error:
        raise PackageError('PACKAGE_READ', path, str(error)) from error


def dependencies(root):
    folder = root / 'dependencies'
    if not folder.exists():
        return []
    if not folder.is_dir() or folder.resolve() != folder:
        raise PackageError('PACKAGE_PATH', folder, 'Se requiere una carpeta local de dependencias.')
    styles = []
    for dependency in sorted(folder.iterdir()):
        if (not re.fullmatch('[a-z][a-z0-9-]*', dependency.name)
                or not dependency.is_dir() or dependency.resolve() != dependency):
            raise PackageError('DEPENDENCY_NAME', dependency, 'Se esperaba una carpeta con nombre de dependencia.')
        versions = sorted(dependency.iterdir())
        if (len(versions) != 1 or not re.fullmatch('[1-9][0-9]*', versions[0].name)
                or not versions[0].is_dir() or versions[0].resolve() != versions[0]):
            raise PackageError('DEPENDENCY_VERSION', dependency, 'Se requiere una sola carpeta de version numerica.')
        styles.append(versions[0] / 'style.ujc')
    return styles


def compile_action(root, action, graph):
    active = []
    compiled = {}

    def compile_file(path, name=None, caller=None, argument=None):
        source = load(path, root, MAX_SOURCE)
        active.append(path)

        def resolve(crate, value, offset):
            line = source.count(b'\n', 0, offset) + 1
            column = offset - source.rfind(b'\n', 0, offset)
            name_text = crate.decode('ascii')
            target = root / 'crates' / name_text / 'main.uj'
            signature = f'{name_text}.run({value if value is not None else ""})'
            edge = {'From': path.relative_to(root).as_posix(),
                    'To': target.relative_to(root).as_posix(),
                    'Reason': signature, 'Line': line}
            if edge not in graph:
                graph.append(edge)
            if target in active or len(active) >= 32:
                code = 'CRATE_CYCLE' if target in active else 'CRATE_DEPTH'
                raise PackageError(code, path, f'No se puede resolver {signature}.',
                                   Line=line, Column=column, RequiredBy=str(target))
            key = target, value
            if key not in compiled:
                try:
                    compiled[key] = compile_file(target, crate, path, value)
                except PackageError as error:
                    error.report.setdefault('RequiredBy', str(path))
                    if error.report['RequiredBy'] == str(path):
                        error.report.setdefault('CallLine', line)
                        error.report.setdefault('CallColumn', column)
                    raise
            return compiled[key]

        try:
            return compile_source(source, resolve, name, argument)
        except Rejection as error:
            offset = error.offset
            line = source.count(b'\n', 0, offset) + 1
            column = offset - source.rfind(b'\n', 0, offset)
            raise PackageError(error.code, path, f'Revisa {error.field}.',
                               Line=line, Column=column, Offset=offset,
                               RequiredBy=str(caller or root)) from error
        finally:
            active.pop()

    return compile_file(action)


def build(root, graph=None):
    root = root.resolve(strict=True)
    action = root / 'action/main.uj'
    markup = root / 'view/main.ujh'
    if graph is None:
        graph = []
    graph.extend(({'From': '.', 'To': 'action/main.uj'}, {'From': '.', 'To': 'view/main.ujh'}))
    paths = dependencies(root)
    local_style = root / 'view/style.ujc'
    if local_style.exists() or local_style.is_symlink():
        paths.append(local_style)
    graph.extend({'From': 'view/main.ujh', 'To': path.relative_to(root).as_posix()} for path in paths)
    bytecode = compile_action(root, action, graph)

    rules, owners = {}, {}
    for path in paths:
        try:
            additions = stylesheet(load(path, root, 16384).decode('ascii'))
        except PackageError as error:
            error.report['RequiredBy'] = str(markup)
            raise
        except ValueError as error:
            raise PackageError('STYLE_INVALID', path, str(error),
                               RequiredBy=str(markup)) from error
        for name, rule in additions.items():
            if name in rules:
                raise PackageError('STYLE_DUPLICATE', path, f'La clase {name} ya existe.',
                                   Previous=str(owners[name]), RequiredBy=str(markup))
            rules[name] = rule
            owners[name] = path

    try:
        display = compile_view_rules(load(markup, root, 16384).decode('ascii'), rules)
    except ET.ParseError as error:
        line, column = error.position
        raise PackageError('VIEW_SYNTAX', markup, str(error), Line=line, Column=column + 1) from error
    except PackageError:
        raise
    except ValueError as error:
        raise PackageError('VIEW_INVALID', markup, str(error), Styles=[str(path) for path in paths]) from error

    return bytecode, display, graph


def graph_report(root, graph, error=None):
    if not root.is_relative_to(PROJECT):
        return
    relative = root.relative_to(PROJECT)
    if not relative.parts:
        return
    target = PROJECT / 'build/ultra-j/graph' / relative / 'report.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if error:
        error = error.copy()
        for key in ('Path', 'RequiredBy', 'Previous'):
            if key in error:
                path = Path(error[key])
                error[key] = path.relative_to(root).as_posix() if path.is_relative_to(root) else None
    payload = dict(Package=relative.as_posix(), Dependencies=graph, Error=error)
    publish(target, (json.dumps(payload, indent=2) + '\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    graph = []
    try:
        bytecode, display, graph = build(root, graph)
        if args.output.resolve().is_relative_to(root):
            raise PackageError('PACKAGE_OUTPUT', args.output, 'La salida va fuera de la carpeta fuente.')
        args.output.mkdir(parents=True, exist_ok=True)
        publish(args.output / 'panel-action.ujb', bytecode)
        publish(args.output / 'panel.ujv', display)
    except PackageError as error:
        print(json.dumps(error.report), file=sys.stderr)
        graph_report(root, graph, error.report)
        return 1
    except OSError as error:
        report = dict(Code='PACKAGE_IO', Path=str(root), Message=str(error))
        print(json.dumps(report), file=sys.stderr)
        try:
            graph_report(root, graph, report)
        except OSError:
            pass
        return 1
    graph_report(root, graph)
    print(json.dumps(dict(Package=args.root.name, Dependencies=graph), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
