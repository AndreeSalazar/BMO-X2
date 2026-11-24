"""Pack and inspect SBEF and diagnose input formats on the host."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from .diagnostics import Rejection
from .importers.elf import MAX_ELF, pack_elf
from .importers.pe import pack_pe, probe_pe
from .profiles import PRODUCER_PROFILES, profile_report
from .sbef.format import (
    FORMAT_VERSION,
    LEGACY_FORMAT_VERSION,
    MAX_IMAGE,
    image_limit,
    inspect,
    load_plan,
)
from .sbef.isa import PROFILES


def positive_bytes(value):
    try:
        amount = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('Se requiere un entero positivo en bytes') from error
    if amount <= 0:
        raise argparse.ArgumentTypeError('Se requiere un entero positivo en bytes')
    return amount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-errors', action='store_true', help='Write structured rejection to stderr')
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('profiles', help='Lista capas HOST y perfiles productores x86-64')
    pack = commands.add_parser('pack')
    pack.add_argument('input', type=Path)
    pack.add_argument('output', type=Path)
    pack.add_argument('--abi', type=int, choices=[0, 1], default=0)
    pack.add_argument('--isa-profile', choices=[profile['Name'] for profile in PROFILES],
                      default='x86-64-v1', help='Declare the minimum x86-64 instruction profile')
    pack.add_argument('--format-version', type=int,
                      choices=[LEGACY_FORMAT_VERSION, FORMAT_VERSION], default=FORMAT_VERSION,
                      help='SBEF wire version; v1 is legacy and implies x86-64-v1')
    pack.add_argument('--max-file-bytes', type=positive_bytes)
    pack.add_argument('--max-mapped-bytes', type=positive_bytes)
    pack.add_argument('--size-report', action='store_true', help='Show file and memory costs by region')
    commands.add_parser('inspect').add_argument('input', type=Path)
    plan = commands.add_parser('plan', help='Emit the validated per-process mapping plan')
    plan.add_argument('input', type=Path)
    plan.add_argument('--profile', choices=['default', 'rmlui-native-v1', 'rmlui-native-fhd'], default='default')
    compare = commands.add_parser('compare', help='Compare the size of two validated SBEF builds')
    compare.add_argument('input', type=Path, metavar='baseline')
    compare.add_argument('candidate', type=Path)
    probe = commands.add_parser('probe')
    probe.add_argument('input', type=Path)
    probe.add_argument('--isa-profile', choices=[profile['Name'] for profile in PROFILES],
                       default='x86-64-v1')
    probe.add_argument('--format-version', type=int,
                       choices=[LEGACY_FORMAT_VERSION, FORMAT_VERSION], default=FORMAT_VERSION)
    for command in (pack, probe):
        command.add_argument('--producer', choices=PRODUCER_PROFILES,
                             help='Declare the producer profile and require its input format')
    args = parser.parse_args()
    try:
        result = run(args)
    except Rejection as error:
        if args.json_errors:
            print(json.dumps(error.report()), file=sys.stderr)
        else:
            detail = f' ({error.actual} > {error.limit} bytes)' if error.limit is not None else ''
            print(f'RED [{error.code}] {error.field} at 0x{error.offset:X}{detail}', file=sys.stderr)
        return 1
    except OSError as error:
        if args.json_errors:
            print(json.dumps(dict(Code='IO', Message=str(error))), file=sys.stderr)
        else:
            print(f'RED [{error}]', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def inspect_file(path):
    with path.open('rb') as file:
        return inspect(file.read(MAX_IMAGE + 1))


def compare_builds(baseline, candidate):
    if baseline['AbiVersion'] != candidate['AbiVersion']:
        raise Rejection('SBEF-COMPARE-ABI', 6, 'abi_version')

    def delta(before, after):
        return dict(BaselineBytes=before, CandidateBytes=after, DeltaBytes=after - before)

    def index(report):
        return {(int(region['Address'], 16), region['Permissions']): region
                for region in report['Regions']}

    before, after = index(baseline), index(candidate)
    regions = []
    for address, permissions in sorted(before.keys() | after.keys()):
        old = before.get((address, permissions), {})
        new = after.get((address, permissions), {})
        costs = {field: delta(old.get(field, 0), new.get(field, 0))
                 for field in ('FileBytes', 'MemoryBytes', 'MappedBytes')}
        regions.append(dict(Address=f'0x{address:X}', Permissions=permissions, **costs))
    return dict(
        Architecture=baseline['Architecture'],
        AbiVersion=baseline['AbiVersion'],
        IsaProfiles=dict(Baseline=baseline['IsaProfile'], Candidate=candidate['IsaProfile'],
                         Same=baseline['IsaProfile'] == candidate['IsaProfile']),
        File=delta(baseline['Bytes'], candidate['Bytes']),
        MappedRegions=delta(sum(region['MappedBytes'] for region in before.values()),
                            sum(region['MappedBytes'] for region in after.values())),
        Regions=regions,
    )


def run(args):
    if args.action == 'profiles':
        return profile_report()
    if args.action == 'inspect':
        return inspect_file(args.input)
    if args.action == 'plan':
        with args.input.open('rb') as file:
            image = file.read(image_limit(args.profile) + 1)
        return load_plan(image, profile=args.profile)
    if args.action == 'compare':
        return compare_builds(inspect_file(args.input), inspect_file(args.candidate))
    if args.format_version == LEGACY_FORMAT_VERSION and args.isa_profile != 'x86-64-v1':
        raise Rejection('SBEF-ISA-VERSION', 24, 'isa_profile')
    with args.input.open('rb') as file:
        data = file.read(MAX_ELF + 1)
    if len(data) > MAX_ELF:
        raise Rejection('IMPORT-SIZE', MAX_ELF, 'file')
    is_pe = data.startswith(b'MZ')
    producer = getattr(args, 'producer', None)
    declared = {}
    if producer is not None:
        profile = PRODUCER_PROFILES[producer]
        signature = b'MZ' if profile['Container'] == 'PE32+' else b'\x7fELF'
        if not data.startswith(signature):
            raise Rejection('HOST-PRODUCER-FORMAT', 0, f'{producer}/{profile["Container"]}')
        declared['ProducerProfile'] = dict(Id=profile['Id'], Selector=producer,
                                           Container=profile['Container'], IdentityAttested=False,
                                           InputSHA256=hashlib.sha256(data).hexdigest())
    if is_pe:
        if args.action == 'probe':
            result = probe_pe(data)
            result.update(declared)
            result['RequestedIsaProfile'] = args.isa_profile
            result['RequestedSBEFFormatVersion'] = args.format_version
            result['ProbeNote'] = 'PE probe inventories the source only; pack emits and validates the declared SBEF profile.'
            return result
        image = pack_pe(data, abi=args.abi, isa_profile=args.isa_profile,
                        format_version=args.format_version)
    else:
        image = pack_elf(data, abi=getattr(args, 'abi', 0), isa_profile=args.isa_profile,
                         format_version=args.format_version)
    report = inspect(image)
    if args.action == 'probe':
        return dict(SourceFormat='ELF64', CanPack=True, SBEF=report, **declared)
    report.update(declared)
    if args.output.resolve() == args.input.resolve():
        raise Rejection('SBEF-OUTPUT-ALIAS', 0, 'output')
    for limit, actual, field, offset in (
        (getattr(args, 'max_file_bytes', None), len(image), 'file_size', 12),
        (getattr(args, 'max_mapped_bytes', None),
         sum(region['MappedBytes'] for region in report['Regions']), 'mapped_bytes', 10),
    ):
        if limit is not None and actual > limit:
            raise Rejection('SBEF-BUDGET', offset, field, actual=actual, limit=limit)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as file:
            temp = Path(file.name)
            file.write(image)
        temp.replace(args.output)
    finally:
        if temp:
            temp.unlink(missing_ok=True)
    if getattr(args, 'size_report', False):
        regions = report['Regions']
        report['SizeReport'] = dict(
            SourceBytes=len(data),
            ContainerBytes=regions[0]['Offset'],
            PayloadBytes=sum(region['FileBytes'] for region in regions),
            MappedRegionBytes=sum(region['MappedBytes'] for region in regions),
            ZeroFillBytes=sum(region['MemoryBytes'] - region['FileBytes'] for region in regions),
            PagePaddingBytes=sum(region['MappedBytes'] - region['MemoryBytes'] for region in regions),
        )
    return report


if __name__ == '__main__':
    raise SystemExit(main())
