"""Report logical file sizes and configured RAM from successful local QEMU runs."""
import hashlib
import json

from scope import ROOT


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def measure(run):
    packet = run/'INICIO.X86'
    config, results = (load(run/name) for name in ('qemu-run.json', 'qemu-results.json'))
    cases = results['Cases']
    if not cases or not all(case['Passed'] is True for case in cases):
        return None
    if results['Passed'] != results['Total'] or [case['Case'] for case in cases] != config['cases']:
        return None
    with packet.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    if digest != config['packet_sha256'] or digest != results['packet_sha256']:
        return None
    packet_bytes = packet.stat().st_size
    if packet_bytes != results['packet_bytes'] or results['body_bytes'] != packet_bytes - 24:
        return None
    sizes = {path.name: path.stat().st_size for path in sorted((run/'build').glob('*.img'))}
    if any(f"puente-{name}.img" not in sizes for name in config['cases']):
        return None
    profile = run/'profile.txt'
    if profile.is_file():
        profile_name = profile.read_text(encoding='utf-8-sig').strip()
    elif results['milestone'] == 'Genesis G1':
        profile_name = 'metal64-0.2'
    else:
        return None
    files = [path for path in run.rglob('*') if path.is_file()]
    return dict(Profile=profile_name,
                Run=run.relative_to(ROOT).as_posix(), CPU=config['cpu'],
                CasesPassed=len(cases), BodyBytes=results['body_bytes'],
                HexFileBytes=(run/'program.hex').stat().st_size, PacketBytes=packet_bytes,
                BridgeBytes=config['bridge_bytes'], VmRamMiB=config['ram_mib'],
                NormalImageBytes=sizes.get('puente-normal.img'), ImageFiles=sizes,
                AllImageBytes=sum(sizes.values()), RunBytes=sum(path.stat().st_size for path in files),
                FrameBytes=cases[0].get('FrameBytes'), MapConventionalBytes=cases[0].get('ConventionalBytes'))


def main():
    build = ROOT/'build/CASM'
    rows = {}
    skipped = []
    for run in sorted(build.glob('run-*'), reverse=True):
        if not (run/'qemu-results.json').is_file():
            continue
        try:
            row = measure(run)
        except (OSError, ValueError, KeyError, TypeError):
            row = None
        if row is None:
            skipped.append(run.name)
        else:
            rows.setdefault(row['Profile'], row)
    compiler = build/'host/casmc.exe'
    print(json.dumps(dict(CompilerHostBytes=compiler.stat().st_size if compiler.is_file() else None,
                          Profiles=sorted(rows.values(), key=lambda row: row['Profile']),
                          SkippedRuns=skipped), indent=2))


if __name__ == '__main__':
    main()
