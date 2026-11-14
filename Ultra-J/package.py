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


def build(root):
    root = root.resolve(strict=True)
    action = root / 'action/main.uj'
    markup = root / 'view/main.ujh'
    source = load(action, root, MAX_SOURCE)
    try:
        bytecode = compile_source(source)
    except Rejection as error:
        offset = error.offset
        line = source.count(b'\n', 0, offset) + 1
        column = offset - source.rfind(b'\n', 0, offset)
        raise PackageError(error.code, action, f'Revisa {error.field}.',
                           Line=line, Column=column, Offset=offset,
                           RequiredBy=str(root)) from error

    paths = dependencies(root)
    local_style = root / 'view/style.ujc'
    if local_style.exists() or local_style.is_symlink():
        paths.append(local_style)
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

    edges = [[root, action], [root, markup], *([markup, path] for path in paths)]
    graph = [{'From': origin.relative_to(root).as_posix(), 'To': target.relative_to(root).as_posix()}
             for origin, target in edges]
    return bytecode, display, graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        bytecode, display, graph = build(args.root)
        if args.output.resolve().is_relative_to(args.root.resolve()):
            raise PackageError('PACKAGE_OUTPUT', args.output, 'La salida va fuera de la carpeta fuente.')
        args.output.mkdir(parents=True, exist_ok=True)
        publish(args.output / 'panel-action.ujb', bytecode)
        publish(args.output / 'panel.ujv', display)
    except PackageError as error:
        print(json.dumps(error.report), file=sys.stderr)
        return 1
    except OSError as error:
        print(json.dumps(dict(Code='PACKAGE_IO', Message=str(error))), file=sys.stderr)
        return 1
    print(json.dumps(dict(Package=args.root.name, Dependencies=graph), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
