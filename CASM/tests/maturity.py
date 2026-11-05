"""Rebuild a pinned baseline and compare the compact host compiler without executing target code."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'CASM'))
from verify import verify


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), capture_output=True, timeout=60, **kwargs)


def corpus():
    cases = [
        ('hello', (ROOT / 'CASM/examples/hello.casm').read_bytes()),
        ('integers', (ROOT / 'CASM/examples/enteros.casm').read_bytes()),
        ('kernel-entry', (ROOT / 'kernel/boot/entry.casm').read_bytes()),
        ('source-max', b'void metal_main(void){return;}' + b' ' * (65536 - len(b'void metal_main(void){return;}'))),
        ('source-over', b' ' * 65537),
        ('late-nul', b'void metal_main(void){return;}' + b' ' * 65000 + b'\0'),
        ('all-strings', b'void metal_main(void){' + b''.join(b'const char s%d[]="' % i + b'a' * 450 + b'";' for i in range(128)) + b'return;}'),
        ('all-integers', b'void metal_main(void){' + b''.join(b'const uint64_t n%d=18446744073709551615;' % i for i in range(128)) + b'return;}'),
        ('negations', b'void metal_main(void){' + b''.join(b'const int64_t n%d=' % i + b'-' * 30 + b'(0);' for i in range(128)) + b'return;}'),
        ('all-decimals', b'void metal_main(void){' + b''.join(b'const int64_t n%d=-9223372036854775808;metal_put_int(n%d);' % (i, i) for i in range(128)) + b'return;}'),
        ('mixed-pools', b'void metal_main(void){' + b''.join(b'const char s%d[]="' % i + b'x' * 400 + b'";const int64_t n%d=1+2*3;metal_put_int(n%d);' % (i, i) for i in range(64)) + b'return;}'),
        ('late-syntax', b'void metal_main(void){' + b''.join(b'const char s%d[]="' % i + b'a' * 450 + b'";' for i in range(128)) + b'unknown();return;}'),
    ]
    name = b'x' * 63
    cases.append(('rpn-dense', b'void metal_main(void){const uint64_t ' + name + b'=0;' + b''.join(b'const uint64_t n%d=' % i + b'+'.join([name] * 60) + b';' for i in range(15)) + b'return;}'))
    rng = random.Random(0xCA5A2026)
    for i in range(256):
        a, b, c = rng.randrange(100000), rng.randrange(100000), rng.randrange(1, 1000)
        cases.append((f'expression-{i}', f'void metal_main(void){{const int64_t n=({a}-{b})*{c};metal_put_int(n);return;}}'.encode()))
    for i in range(64):
        # Both valid edge arithmetic and specific failures, chosen independently of the emitter.
        kind = i % 4
        value = 255 if kind == 0 else 256 if kind == 1 else 0 if kind == 2 else 1
        expr = str(value) if kind < 2 else f'{value}/0'
        cases.append((f'rejection-{i}', f'void metal_main(void){{const uint8_t n={expr};return;}}'.encode()))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--baseline-ref', default='d2575a8')
    args = parser.parse_args()
    metadata = json.loads((args.compiler.resolve().parent / 'toolchain.json').read_text(encoding='utf-8-sig'))
    if metadata['executable_sha256'] != hashlib.sha256(args.compiler.read_bytes()).hexdigest():
        raise ValueError('Compiler differs from its recorded build')
    for source in metadata['sources']:
        if hashlib.sha256((ROOT / source['ruta']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Compiler build is stale: '+source['ruta'])
    output = ROOT / 'build/CASM/maturity'
    output.mkdir(parents=True, exist_ok=True)
    source_paths = ['src/casm.h', 'src/main.c', 'src/frontend.c', 'src/emitter.c']
    base = output / 'baseline'
    base.mkdir(exist_ok=True)
    for rel in source_paths:
        data = subprocess.check_output(['git', 'show', f'{args.baseline_ref}:CASM/{rel}'], cwd=ROOT)
        target = base / Path(rel).name
        target.write_bytes(data)
    measure = '#include "casm.h"\n#include <stdio.h>\nint main(void){printf("{\\\"program_bytes\\\":%zu}\\n",sizeof(CasmProgram));return 0;}\n'
    (base / 'measure.c').write_text(measure, encoding='ascii', newline='\n')
    flags = ['-std=c11', '-D_CRT_SECURE_NO_WARNINGS', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O2']
    toolchain = subprocess.check_output([args.cc, '--version'], text=True).strip()
    if metadata['flags'] != flags or metadata['compiler'].splitlines() != toolchain.splitlines():
        raise ValueError('Baseline and current compiler require identical host toolchain and flags')
    baseline = base / 'casmc.exe'
    for sources, target in [([base / n for n in ('main.c', 'frontend.c', 'emitter.c')], baseline),
                            ([base / 'measure.c'], base / 'measure.exe')]:
        built = run([args.cc, *flags, *sources, '-o', target])
        if built.returncode:
            raise RuntimeError(built.stderr.decode(errors='replace'))
    old_sizes = json.loads(subprocess.check_output([base / 'measure.exe']))
    workspace = ROOT / 'build/CASM/host/workspace.exe'
    built = run([args.cc, *flags, ROOT / 'CASM/tests/workspace.c', ROOT / 'CASM/src/model/storage.c', '-o', workspace])
    if built.returncode:
        raise RuntimeError(built.stderr.decode(errors='replace'))
    current_sizes = json.loads(subprocess.check_output([workspace]))
    records = []
    with tempfile.TemporaryDirectory(prefix='differential-', dir=output) as temporary:
        work = Path(temporary)
        for index, (name, source) in enumerate(corpus()):
            frozen = work / 'source.casm'; frozen.write_bytes(source)
            observations = []
            for variant, compiler in enumerate((baseline, args.compiler)):
                hp, ip = work / f'{index}-{variant}.hex', work / f'{index}-{variant}.json'
                result = run([compiler, frozen, hp, ip])
                artifacts = (hp.read_bytes(), ip.read_bytes()) if result.returncode == 0 else None
                if result.returncode == 0:
                    packet, _ = verify(frozen, hp, ip)
                else:
                    if hp.exists() or ip.exists():
                        raise AssertionError(f'{name}: rejected compilation emitted artifacts')
                    packet = None
                observations.append((result.returncode, result.stdout, result.stderr, artifacts, packet))
            if observations[0] != observations[1]:
                raise AssertionError(f'{name}: baseline and current differ: {observations[0][:3]} / {observations[1][:3]}')
            records.append({'case': name, 'accepted': observations[1][0] == 0, 'identical': True})
    old, new = old_sizes['program_bytes'], current_sizes['program_bytes']
    if not new < old:
        raise AssertionError('Host workspace did not shrink')
    report = {'schema': 1, 'baseline_commit': args.baseline_ref, 'scope': 'Host sizeof(CasmProgram), not RSS or Ring 0 RAM/power/cycles',
              'host': sys.platform, 'toolchain': toolchain.splitlines()[0],
              'measured_sources': {s['ruta']: s['sha256'] for s in metadata['sources']},
              'baseline_program_bytes': old, 'program_bytes': new, 'saved_bytes': old-new,
              'reduction_percent': round(100*(old-new)/old, 3), 'workspace': current_sizes,
              'baseline_executable_bytes': baseline.stat().st_size, 'executable_bytes': args.compiler.stat().st_size,
              'compiler_sha256': hashlib.sha256(args.compiler.read_bytes()).hexdigest(),
              'differential_cases': len(records), 'accepted': sum(r['accepted'] for r in records),
              'rejected': sum(not r['accepted'] for r in records), 'hex_ir_packet_diagnostics_identical': True,
              'target_code_executed': False, 'cases': records}
    (output / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
