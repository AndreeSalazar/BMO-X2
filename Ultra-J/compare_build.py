"""Measure HOST artifact generation for the two object demos."""
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter


ULTRA_J = Path(__file__).resolve().parent
PROJECT = ULTRA_J.parent
RUNS = 11


def timed(command):
    start = perf_counter()
    subprocess.run(command, cwd=PROJECT, check=True, capture_output=True)
    return (perf_counter() - start) * 1000


def compare(output):
    bytecode = output / 'object-demo.ujb'
    elf = output / 'object-demo.elf'
    sbef = output / 'object-demo.sbef'
    linker = Path(os.environ['ProgramFiles']) / 'LLVM/bin/ld.lld.exe'
    compile_uj = [sys.executable, '-B', ULTRA_J / 'compiler.py',
                  ULTRA_J / 'examples/ObjectDemo.uj', bytecode]
    compile_rust = [
        'rustc', '--edition=2021', '--target=x86_64-unknown-none',
        '-C', 'panic=abort', '-C', 'opt-level=z', '-C', 'relocation-model=static',
        '-C', 'force-unwind-tables=no', '-C', 'strip=symbols', '-C', 'lto=fat',
        '-C', f'linker={linker}', '-C', 'linker-flavor=ld',
        '-C', 'link-arg=-Ttools/desktop/external.ld',
        ULTRA_J / 'examples/object_demo.rs', '-o', elf,
    ]
    pack = [sys.executable, '-B', PROJECT / 'tools/sbef.py', 'pack',
            elf, sbef, '--abi', '1', '--size-report']
    for command in (compile_uj, compile_rust, pack):
        timed(command)
    uj_times, elf_times, sbef_times = [], [], []
    for index in range(RUNS):
        if index % 2:
            uj_times.append(timed(compile_uj))
        build_ms = timed(compile_rust)
        pack_ms = timed(pack)
        elf_times.append(build_ms)
        sbef_times.append(build_ms + pack_ms)
        if index % 2 == 0:
            uj_times.append(timed(compile_uj))
    return {
        'Evidence': 'HOST',
        'Runs': RUNS,
        'UltraJUJBC': {'MedianMs': round(median(uj_times), 1), 'Bytes': bytecode.stat().st_size},
        'RustELF': {'MedianMs': round(median(elf_times), 1), 'Bytes': elf.stat().st_size},
        'RustSBEF': {'MedianMs': round(median(sbef_times), 1), 'Bytes': sbef.stat().st_size},
    }


if __name__ == '__main__':
    build = PROJECT / 'build'
    build.mkdir(exist_ok=True)
    try:
        with TemporaryDirectory(prefix='ultra-j-compare-', dir=build) as directory:
            print(json.dumps(compare(Path(directory)), indent=2))
    except subprocess.CalledProcessError as error:
        sys.stderr.buffer.write(error.stderr)
        raise SystemExit(error.returncode) from error
