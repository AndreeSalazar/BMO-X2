"""Pack and inspect SBEF and diagnose input formats on the host."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from sbef_host.diagnostics import Rejection
from sbef_host.elf import MAX_ELF, pack_elf
from sbef_host.format import MAX_IMAGE, inspect
from sbef_host.pe import probe_pe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-errors', action='store_true', help='Write structured rejection to stderr')
    commands = parser.add_subparsers(dest='action', required=True)
    pack = commands.add_parser('pack')
    pack.add_argument('input', type=Path)
    pack.add_argument('output', type=Path)
    commands.add_parser('inspect').add_argument('input', type=Path)
    commands.add_parser('probe').add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        result = run(args)
    except Rejection as error:
        if args.json_errors:
            print(json.dumps(error.report()), file=sys.stderr)
        else:
            print(f'RED [{error.code}] {error.field} at 0x{error.offset:X}', file=sys.stderr)
        return 1
    except OSError as error:
        if args.json_errors:
            print(json.dumps(dict(Code='IO', Message=str(error))), file=sys.stderr)
        else:
            print(f'RED [{error}]', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def run(args):
    with args.input.open('rb') as file:
        data = file.read((MAX_IMAGE if args.action == 'inspect' else MAX_ELF) + 1)
    if args.action == 'inspect':
        return inspect(data)
    if len(data) > MAX_ELF:
        raise Rejection('IMPORT-SIZE', MAX_ELF, 'file')
    if data.startswith(b'MZ'):
        inventory = probe_pe(data)
        if args.action == 'probe':
            return inventory
        blocker = inventory['Blockers'][0]
        raise Rejection(blocker['Code'], blocker['Offset'], blocker['Field'])
    image = pack_elf(data)
    report = inspect(image)
    if args.action == 'probe':
        return dict(SourceFormat='ELF64', CanPack=True, SBEF=report)
    if args.output.resolve() == args.input.resolve():
        raise Rejection('SBEF-OUTPUT-ALIAS', 0, 'output')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as file:
            temp = Path(file.name)
            file.write(image)
        temp.replace(args.output)
    finally:
        if temp:
            temp.unlink(missing_ok=True)
    return report


if __name__ == '__main__':
    raise SystemExit(main())
