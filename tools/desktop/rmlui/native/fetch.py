"""Fetch pinned native build inputs into build/deps; no system installation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / 'build/deps'
LOCK = Path(__file__).with_name('dependencies.lock.json')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pinned_archive(entry, download=False):
    archive = CACHE / 'downloads' / entry['archive']
    if not archive.is_file() and download:
        archive.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(entry['url'], archive)
    if not archive.is_file() or digest(archive) != entry['sha256']:
        raise ValueError('Missing or untrusted archive: ' + str(archive))
    return archive


def extract(entry, archive):
    destination = (CACHE / entry['folder']).resolve()
    destination.relative_to(CACHE.resolve())
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as bundle:
        prefix = entry['prefix'] + '/'
        members = []
        for member in bundle.getmembers():
            if not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix):]
            if not relative:
                continue
            selected = entry.get('select')
            if selected and not any(relative == item or relative.startswith(item + '/') for item in selected):
                continue
            # Native Windows extraction: regular files/directories only. Never follow links.
            if not (member.isfile() or member.isdir()) or '\\' in relative:
                raise ValueError('Unsupported archive member: ' + member.name)
            (destination / relative).resolve().relative_to(destination)
            member.name = relative
            members.append(member)
        if not members:
            raise ValueError('Empty pinned extraction: ' + entry['archive'])
        bundle.extractall(destination, members=members, filter='data')


def check_sources():
    for entry in json.loads(LOCK.read_text())['dependencies']:
        archive = pinned_archive(entry)
        # Compare extracted source bytes with the pinned archive, not a trusted marker.
        destination = CACHE / entry['folder']
        expected = set()
        with tarfile.open(archive) as bundle:
            prefix = entry['prefix'] + '/'
            for member in bundle.getmembers():
                if not member.isfile() or not member.name.startswith(prefix):
                    continue
                relative = member.name[len(prefix):]
                selected = entry.get('select')
                if selected and not any(relative == item or relative.startswith(item + '/') for item in selected):
                    continue
                path = destination / relative
                expected.add(path.resolve())
                if not path.is_file() or digest(path) != hashlib.sha256(bundle.extractfile(member).read()).hexdigest():
                    raise ValueError('Native input changed: ' + str(path))
        for path in destination.rglob('*'):
            if path.is_symlink() or (path.is_file() and path.resolve() not in expected):
                raise ValueError('Unexpected native input: ' + str(path))
    lock = json.loads((Path(__file__).parent.parent / 'dependencies.lock.json').read_text())
    for entry in lock['dependencies']:
        path = CACHE / entry['folder']
        commit = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=all'], text=True)
        if commit != entry['commit'] or dirty:
            raise ValueError('Engine input changed: ' + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only validation of archives and extracted inputs')
    args = parser.parse_args()
    if not args.check:
        for entry in json.loads(LOCK.read_text())['dependencies']:
            extract(entry, pinned_archive(entry, download=True))
    check_sources()
    print('PASS: pinned native sources; no system installation')


if __name__ == '__main__':
    main()
