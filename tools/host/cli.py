"""Pack and inspect SBEF and diagnose input formats on the host."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

from .diagnostics import Rejection
from .file_catalog import catalog_directory
from .importers.elf import MAX_ELF, pack_elf
from .importers.pe import pack_pe, pack_pe_tls, pack_pe_with_dll, probe_pe
from .pe_admission import explain_pe, markdown_admission
from .profiles import PRODUCER_PROFILES, profile_report
from .toolchains.msvc_catalog import CATALOG as MSVC_CATALOG
from .toolchains.windows_catalog import LEVELS as WINDOWS_LEVELS, import_coverage
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


def sha256_hex(value):
    if not re.fullmatch('[0-9a-fA-F]{64}', value):
        raise argparse.ArgumentTypeError('Se requieren 64 digitos hexadecimales de SHA-256')
    return value.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-errors', action='store_true', help='Write structured rejection to stderr')
    commands = parser.add_subparsers(dest='action', required=True)
    profiles = commands.add_parser('profiles', help='Lista capas HOST y perfiles productores x86-64')
    profiles.add_argument('--producer', choices=PRODUCER_PROFILES)
    catalog_filter = profiles.add_mutually_exclusive_group()
    catalog_filter.add_argument('--category', choices=MSVC_CATALOG, help='Filtra el catalogo detallado de MSVC')
    catalog_filter.add_argument('--windows-level', choices=('todos', *WINDOWS_LEVELS),
                                help='Lista dependencias de Windows por nivel')
    profiles.add_argument('--format', choices=('json', 'markdown'), default='json')
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
    pack.add_argument('--expected-sha256', type=sha256_hex, help='Require the reviewed input SHA-256')
    pack.add_argument('--expected-dll-sha256', type=sha256_hex, help='Require the reviewed companion DLL SHA-256')
    pack.add_argument('--max-mapped-bytes', type=positive_bytes)
    pack.add_argument('--size-report', action='store_true', help='Show file and memory costs by region')
    pack.add_argument('--explain', action='store_true', help='Explain default PE admission on rejection')
    dll_profiles = pack.add_mutually_exclusive_group()
    dll_profiles.add_argument('--with-dll', type=Path, help='Bind one fixed Win64 DLL to a PE32+ console image')
    dll_profiles.add_argument('--with-dll-lifecycle', type=Path, help='Bind a fixed Win64 DLL including its entry export')
    dll_profiles.add_argument('--static-tls', action='store_true', help='Materialize the fixed Win64 TLS profile')
    commands.add_parser('inspect').add_argument('input', type=Path)
    catalog = commands.add_parser('catalog', help='Inventaria archivos y dependencias sin ejecutarlos')
    catalog.add_argument('root', type=Path)
    catalog.add_argument('--game', metavar='TITLE', help='Declara un juego y propone su carpeta Game')
    catalog.add_argument('--deep', action='store_true',
                         help='Anota roles sugeridos y examina miembros ZIP con presupuestos acotados')
    plan = commands.add_parser('plan', help='Emit the validated per-process mapping plan')
    plan.add_argument('input', type=Path)
    plan.add_argument('--profile', choices=['default', 'rmlui-native-v1', 'rmlui-native-fhd'], default='default')
    compare = commands.add_parser('compare', help='Compare the size of two validated SBEF builds')
    compare.add_argument('input', type=Path, metavar='baseline')
    compare.add_argument('candidate', type=Path)
    probe = commands.add_parser('probe')
    probe.add_argument('input', type=Path)
    probe.add_argument('--format', choices=('json', 'markdown'), default='json')
    probe.add_argument('--isa-profile', choices=[profile['Name'] for profile in PROFILES],
                       default='x86-64-v1')
    probe.add_argument('--format-version', type=int,
                       choices=[LEGACY_FORMAT_VERSION, FORMAT_VERSION], default=FORMAT_VERSION)
    for command in (pack, probe):
        command.add_argument('--producer', choices=PRODUCER_PROFILES,
                             help='Declare the producer profile and require its input format')
    args = parser.parse_args()
    if args.action == 'profiles' and args.producer != 'msvc' and (args.category or args.windows_level):
        profiles.error('--category y --windows-level requieren --producer msvc')
    if args.action == 'pack' and args.expected_dll_sha256 and not (args.with_dll or args.with_dll_lifecycle):
        pack.error('--expected-dll-sha256 requiere un perfil con DLL')
    try:
        result = run(args)
    except Rejection as error:
        admission = error.admission
        if args.json_errors:
            report = error.report()
            if admission is not None:
                report['Admission'] = admission
            print(json.dumps(report), file=sys.stderr)
        else:
            detail = f' ({error.actual} > {error.limit} bytes)' if error.limit is not None else ''
            print(f'RED [{error.code}] {error.field} at 0x{error.offset:X}{detail}', file=sys.stderr)
            if admission is not None:
                print(markdown_admission(admission), file=sys.stderr)
        return 1
    except OSError as error:
        if args.json_errors:
            print(json.dumps(dict(Code='IO', Message=str(error))), file=sys.stderr)
        else:
            print(f'RED [{error}]', file=sys.stderr)
        return 1
    if args.action == 'profiles' and args.format == 'markdown':
        print(markdown_catalog(result))
    elif args.action == 'probe' and args.format == 'markdown' and 'Admission' in result:
        print(markdown_admission(result['Admission']))
    else:
        print(json.dumps(result, indent=2))
    return 0


def markdown_catalog(report):
    profiles = {profile['Selector']: profile for profile in report['Profiles']}
    title = 'HOST' if len(profiles) > 1 else next(iter(profiles)).upper()
    lines = [f'# {title} / {report["Target"]}']
    for selector, work in report.get('ProducerWorkPlan', {}).items():
        profile = profiles[selector]
        lines.extend(('', f'## {selector}', '', work['Work'], '',
                      f'- **Productor** {profile["Producer"]}',
                      f'- **Objetos y ejecutable** {profile["ObjectFormat"]} / {profile["ExecutableFormat"]}',
                      f'- **Convencion de llamadas** {work["CallingConvention"]}',
                      f'- **Admision** {profile["AdmissionEvidence"]}',
                      f'- **Ejecucion** {profile["ExecutionEvidence"]}'))
        lines.extend(f'- [{label}]({path})' for label, path in work['Evidence'])
        lines.extend(('', '### Siguientes pruebas', ''))
        lines.extend(f'{order}. **{name}**. {criterion}'
                     for order, (name, criterion) in enumerate(work['Milestones'], 1))
    if report.get('CapabilityGroups'):
        lines.extend(('', *(f'- **{state.upper()}** {description}'
                            for state, description in report['CapabilityStates'].items())))
    for group in report.get('CapabilityGroups', []):
        lines.extend(('', f'## {group["Name"]}', ''))
        for item in group['Capabilities']:
            entry = f'- **{item["Name"]}** ({item["State"].upper()}). {item["Boundary"]}'
            if 'Evidence' in item:
                entry += f' [Evidencia]({item["Evidence"]})'
            lines.append(entry)
    for level in report.get('WindowsImportCatalog', []):
        lines.extend(('', f'## Dependencias Windows / {level["Level"]}', '',
                      'Inventario de familias. La presencia de una DLL no acredita ejecucion.', ''))
        for group in level['Groups']:
            names = [*group['DLLs'], *(prefix + '*.dll' for prefix in group['ContractPrefixes'])]
            lines.append(f'- **{group["Name"]}**')
            lines.extend(f'  - `{name}`' for name in names)
    return '\n'.join(lines)


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
        return profile_report(getattr(args, 'producer', None), getattr(args, 'category', None),
                              getattr(args, 'windows_level', None))
    if args.action == 'inspect':
        return inspect_file(args.input)
    if args.action == 'catalog':
        return catalog_directory(args.root, deep=getattr(args, 'deep', False), game=getattr(args, 'game', None))
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
    expected = getattr(args, 'expected_sha256', None)
    if expected is not None and hashlib.sha256(data).hexdigest() != expected:
        raise Rejection('HOST-CATALOG-HASH', 0, 'input')
    is_pe = data.startswith(b'MZ')
    lifecycle = getattr(args, 'with_dll_lifecycle', None)
    dll_input = lifecycle or getattr(args, 'with_dll', None)
    producer = getattr(args, 'producer', None)
    declared = {'ReviewedInputSHA256': expected} if expected is not None else {}
    if producer is not None:
        profile = PRODUCER_PROFILES[producer]
        signature = b'MZ' if profile['Container'] == 'PE32+' else b'\x7fELF'
        if not data.startswith(signature):
            raise Rejection('HOST-PRODUCER-FORMAT', 0, f'{producer}/{profile["Container"]}')
        declared['ProducerProfile'] = dict(Id=profile['Id'], Selector=producer,
                                           Container=profile['Container'], IdentityAttested=False,
                                           InputSHA256=hashlib.sha256(data).hexdigest())
    if dll_input:
        if not is_pe:
            raise Rejection('PE-DLL-PROFILE', 0, 'PE32+ EXE')
        if args.output.resolve() == dll_input.resolve():
            raise Rejection('SBEF-OUTPUT-ALIAS', 0, 'output')
        with dll_input.open('rb') as file:
            dll = file.read(MAX_ELF + 1)
        if len(dll) > MAX_ELF:
            raise Rejection('IMPORT-SIZE', MAX_ELF, 'DLL.file')
        dll_hash = hashlib.sha256(dll).hexdigest()
        expected_dll = getattr(args, 'expected_dll_sha256', None)
        if expected_dll is not None and dll_hash != expected_dll:
            raise Rejection('HOST-CATALOG-HASH', 0, 'DLL.file')
        image, dependency = pack_pe_with_dll(data, dll, abi=args.abi, isa_profile=args.isa_profile,
                                             format_version=args.format_version, lifecycle=lifecycle is not None)
        declared['LinkedModule'] = dict(dependency, SHA256=dll_hash, Bytes=len(dll))
    elif getattr(args, 'static_tls', False):
        image, tls = pack_pe_tls(data, abi=args.abi, isa_profile=args.isa_profile,
                                 format_version=args.format_version)
        declared['StaticTLS'] = tls
    elif is_pe:
        if args.action == 'probe':
            result = probe_pe(data)
            if 'ImportInventoryError' not in result:
                result['ImportCoverage'] = import_coverage(result.get('Imports', []))
            result['Admission'] = explain_pe(result)
            result.update(declared)
            result['RequestedIsaProfile'] = args.isa_profile
            result['RequestedSBEFFormatVersion'] = args.format_version
            result['ProbeNote'] = 'PE probe inventories the source only; pack emits and validates the declared SBEF profile.'
            return result
        try:
            image = pack_pe(data, abi=args.abi, isa_profile=args.isa_profile,
                            format_version=args.format_version)
        except Rejection as error:
            if getattr(args, 'explain', False):
                try:
                    inventory = probe_pe(data)
                except Rejection:
                    inventory = dict(CanPack=False, Blockers=[error.report()])
                if not any(blocker['Code'] == error.code for blocker in inventory['Blockers']):
                    inventory['Blockers'].append(error.report())
                    inventory['CanPack'] = False
                error.admission = explain_pe(inventory)
            raise
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
