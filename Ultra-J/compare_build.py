"""Measure HOST artifact generation for the two object demos."""
import json
import os
from pathlib import Path
from queue import Empty, Queue
from statistics import median
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import perf_counter, sleep

from compiler import compile_source


ULTRA_J = Path(__file__).resolve().parent
PROJECT = ULTRA_J.parent
RUNS = 11


def timed(command):
    start = perf_counter()
    subprocess.run(command, cwd=PROJECT, check=True, capture_output=True)
    return (perf_counter() - start) * 1000


def watch_times(output):
    source = output / 'watch.uj'
    bytecode = output / 'watch.ujb'
    original = (ULTRA_J / 'examples/ObjectDemo.uj').read_bytes()
    edited = original.replace(b'panel.show();', b'enter.activate();', 1)
    samples = (original, edited)
    expected = tuple(map(compile_source, samples))
    source.write_bytes(original)

    published = Queue()

    def read_reports():
        for line in process.stdout:
            published.put((perf_counter(), line))

    def wait_for(binary):
        try:
            received, _ = published.get(timeout=5)
        except Empty as error:
            raise RuntimeError('El compilador en modo watch no publico el bytecode esperado.') from error
        if bytecode.read_bytes() != binary:
            raise RuntimeError('El binario publicado difiere del esperado.')
        return received

    elapsed = []
    command = [sys.executable, '-B', ULTRA_J / 'compiler.py', source, bytecode, '--watch']
    with subprocess.Popen(command, cwd=PROJECT, stdout=subprocess.PIPE) as process:
        reader = Thread(target=read_reports, daemon=True)
        reader.start()
        try:
            wait_for(expected[0])
            for index in range(RUNS):
                sample = (index + 1) % 2
                # Vary the interval between saves to sample different polling phases.
                sleep(0.013 + index * 0.007)
                start = perf_counter()
                saved = source.with_suffix('.tmp')
                saved.write_bytes(samples[sample])
                saved.replace(source)
                elapsed.append((wait_for(expected[sample]) - start) * 1000)
        finally:
            if process.poll() is None:
                process.terminate()
            reader.join(timeout=5)
    return elapsed


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
    source = (ULTRA_J / 'examples/ObjectDemo.uj').read_bytes()
    compile_ms = []
    for _ in range(1001):
        start = perf_counter()
        compile_source(source)
        compile_ms.append((perf_counter() - start) * 1000)
    return {
        'Evidence': 'HOST',
        'Runs': RUNS,
        'UltraJUJBC': {'MedianMs': round(median(uj_times), 1), 'Bytes': bytecode.stat().st_size},
        'UltraJInMemory': {'MedianMs': round(median(compile_ms), 3), 'Runs': len(compile_ms)},
        'UltraJWatch': {'MedianMs': round(median(watch_times(output)), 1)},
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
