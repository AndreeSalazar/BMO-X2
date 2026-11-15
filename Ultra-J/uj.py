"""Create and run folder-based ULTRA-J crates on HOST."""
import argparse
import json
from pathlib import Path
import re
import sys

from compiler import RESERVED, publish
from package import PackageError, compile_action, graph_report
from runtime import Rejection, run


def new_crate(name):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', name) or name.encode('ascii') in RESERVED:
        raise PackageError('CRATE_NAME', name, 'Usa un nombre de crate en minusculas.')
    root = Path.cwd() / name
    root.mkdir()
    source = (
        f'class {name.capitalize()} {{\n'
        '    void run() {\n'
        '        Console.println("Hola mundo");\n'
        '        return;\n'
        '    }\n'
        '}\n'
    )
    publish(root / 'main.uj', source.encode('ascii'))
    return root


def run_crate(root):
    graph = [{'From': '.', 'To': 'main.uj'}]
    try:
        program = compile_action(root, root / 'main.uj', graph)
        result = run(program)
        output = root / 'build'
        if output.resolve() != output:
            raise PackageError('CRATE_OUTPUT', output, 'La salida debe quedar dentro del crate.')
        output.mkdir(exist_ok=True)
        publish(output / 'main.ujb', program)
    except PackageError as error:
        graph_report(root, graph, error.report)
        raise
    graph_report(root, graph)
    return result['Output']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new')
    new.add_argument('kind', choices=('crate', 'driver'))
    new.add_argument('name')
    new.add_argument('--pci')
    driver = commands.add_parser('driver')
    driver.add_argument('action', choices=('check', 'prepare'))
    commands.add_parser('run', aliases=['Run'])
    args = parser.parse_args()
    try:
        if args.command == 'new':
            if args.kind == 'driver':
                from driver import new_driver
                print(new_driver(args.name, args.pci))
            else:
                if args.pci:
                    raise PackageError('CRATE_ARGUMENT', args.name, '--pci solo se usa con drivers.')
                print(new_crate(args.name))
        elif args.command == 'driver':
            from driver import check_driver, prepare_driver
            action = check_driver if args.action == 'check' else prepare_driver
            print(json.dumps(action(Path.cwd().resolve()), indent=2))
        else:
            for line in run_crate(Path.cwd().resolve()):
                print(line)
    except PackageError as error:
        print(json.dumps(error.report), file=sys.stderr)
        return 1
    except (OSError, Rejection) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
