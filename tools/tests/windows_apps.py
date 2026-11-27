"""Prueba aplicaciones Win64 en Windows y verifica su admision por HOST."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HOST = Path(__file__).resolve().parents[1] / 'sbef.py'
SEED_SQL = (
    'BEGIN; CREATE TABLE scores(id INTEGER PRIMARY KEY, score INTEGER NOT NULL);'
    'WITH RECURSIVE ids(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM ids WHERE n<1000)'
    ' INSERT INTO scores SELECT n,n*2 FROM ids; COMMIT;'
    'BEGIN; UPDATE scores SET score=0 WHERE id<500; ROLLBACK;'
)
SELECT_SQL = 'SELECT count(*),sum(score) FROM scores;'
EXPECTED_SQL = ['1000|1001000']


def invoke(*command, cwd, expected=0, data=None):
    result = subprocess.run(command, cwd=cwd, input=data, capture_output=True, timeout=90)
    if result.returncode != expected:
        stderr = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f'{Path(command[0]).name}: salida {result.returncode}, '
                           f'esperada {expected}. {stderr}')
    return result.stdout


def sqlite(exe, work):
    cli = (exe, '-batch', '-bail')
    memory = invoke(*cli, ':memory:', SEED_SQL + SELECT_SQL, cwd=work).decode().splitlines()
    database = work / 'scores.db'
    invoke(*cli, database, SEED_SQL, cwd=work)
    reopen = invoke(*cli, database, 'PRAGMA integrity_check;' + SELECT_SQL,
                    cwd=work).decode().splitlines()
    invoke(*cli, database, 'INSERT INTO scores VALUES(1,9);', cwd=work, expected=1)
    after_error = invoke(*cli, database, SELECT_SQL, cwd=work).decode().splitlines()
    if memory != EXPECTED_SQL or reopen != ['ok', *EXPECTED_SQL] or after_error != EXPECTED_SQL:
        raise RuntimeError(f'SQLite: resultados inesperados {memory}, {reopen}, {after_error}')
    return dict(Memory=memory, Reopened=reopen, AfterConstraintError=after_error)


def gzip_roundtrip(exe, work, data):
    compressed = invoke(exe, '-c', cwd=work, data=data)
    decoded = invoke(exe, '-d', '-c', cwd=work, data=compressed)
    if decoded != data:
        raise RuntimeError('minigzip: contenido restaurado distinto')
    return dict(InputBytes=len(data), CompressedBytes=len(compressed),
                RestoredSHA256=hashlib.sha256(decoded).hexdigest())


def archive_roundtrip(exe, work, data, *, seven_zip):
    source = work / 'source'
    source.mkdir()
    files = {'empty.txt': b'', 'subdir/compresi\u00f3n.bin': data}
    for name, content in files.items():
        path = source / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
    archive = work / ('sample.7z' if seven_zip else 'sample.tar.gz')
    restored = work / 'restored'
    restored.mkdir()
    if seven_zip:
        invoke(exe, 'a', archive, 'empty.txt', 'subdir', cwd=source)
        invoke(exe, 'l', archive, cwd=work)
        invoke(exe, 't', archive, cwd=work)
        invoke(exe, 'x', archive, f'-o{restored}', cwd=work)
    else:
        invoke(exe, '-czf', archive, 'empty.txt', 'subdir', cwd=source)
        invoke(exe, '-tzf', archive, cwd=work)
        invoke(exe, '-xzf', archive, '-C', restored, cwd=work)
    actual = {path.relative_to(restored).as_posix(): path.read_bytes()
              for path in restored.rglob('*') if path.is_file()}
    if actual != files:
        raise RuntimeError(f'{exe.name}: rutas o contenido restaurado distinto')
    return dict(ArchiveBytes=archive.stat().st_size,
                RestoredSHA256={name: hashlib.sha256(content).hexdigest()
                                for name, content in actual.items()})


def check_host(exe, producer, work):
    profile = ('--producer', producer) if producer else ()
    inventory = json.loads(invoke(sys.executable, '-B', HOST, 'probe', exe, *profile, cwd=work))
    if inventory['Architecture'] != 'x86-64':
        raise RuntimeError(f'{exe.name}: se requiere un PE x86-64')
    package = work / 'application.sbef'
    build = subprocess.run([sys.executable, '-B', HOST, '--json-errors', 'pack', exe,
                            package, '--abi', '1', *profile],
                           cwd=work, capture_output=True, timeout=90)
    accepted = build.returncode == 0
    if accepted != inventory['CanPack'] or package.exists() != accepted:
        raise RuntimeError(f'{exe.name}: discrepancia entre probe, pack y archivo SBEF')
    rejection = None if accepted else json.loads(build.stderr)
    if rejection is not None and rejection['Code'] not in {
            item['Code'] for item in inventory['Blockers']}:
        raise RuntimeError(f'{exe.name}: pack rechazo por un motivo sin inventariar: {rejection}')
    return dict(Probe=inventory, PackAccepted=accepted, PackRejection=rejection, QemuRan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite-msvc', type=Path, required=True)
    parser.add_argument('--sqlite-clang-cl', type=Path, required=True)
    parser.add_argument('--minigzip-msvc', type=Path)
    parser.add_argument('--minigzip-clang-cl', type=Path)
    parser.add_argument('--tar', type=Path)
    parser.add_argument('--seven-zip', type=Path)
    parser.add_argument('--notepad-plus-plus', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('El banco requiere Windows para ejecutar los PE de referencia.')

    data = hashlib.shake_256(b'BMO-X2 HOST archive').digest(131072) + b'BMO-X2\0' * 65536
    cases = (
        ('sqlite-msvc', args.sqlite_msvc, 'msvc', sqlite),
        ('sqlite-clang-cl', args.sqlite_clang_cl, 'clang-cl', sqlite),
        ('minigzip-msvc', args.minigzip_msvc, 'msvc', gzip_roundtrip),
        ('minigzip-clang-cl', args.minigzip_clang_cl, 'clang-cl', gzip_roundtrip),
        ('tar', args.tar, None, archive_roundtrip),
        ('7-zip', args.seven_zip, None, archive_roundtrip),
        ('notepad++', args.notepad_plus_plus, None, None),
    )
    reports = {}
    for name, exe, producer, action in cases:
        if exe is None:
            continue
        exe = exe.resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix='bmo-host-app-') as folder:
            work = Path(folder)
            windows = None
            if action is sqlite:
                windows = sqlite(exe, work)
            elif action is gzip_roundtrip:
                windows = gzip_roundtrip(exe, work, data)
            elif action is archive_roundtrip:
                windows = archive_roundtrip(exe, work, data, seven_zip=name == '7-zip')
            reports[name] = dict(Binary=str(exe), Windows=windows,
                                 Host=check_host(exe, producer, work))
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
