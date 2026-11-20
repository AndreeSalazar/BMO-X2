"""Comprueba los cuatro binarios de una release GSP GA10x en HOST."""

import argparse
import hashlib
import json
from pathlib import Path


PROFILES = Path(__file__).with_name('ga10x-firmware.json')


def verify(directory, release, profile):
    checked = {}
    for role, (expected_size, expected_hash) in profile['files'].items():
        path = directory / f'{role}-{release}.bin'
        if not path.is_file():
            raise ValueError(f'{role}: falta {path.name}')
        if path.stat().st_size != expected_size:
            raise ValueError(f'{role}: longitud distinta de la referencia {release}')
        digest = hashlib.sha256()
        read_bytes = 0
        with path.open('rb') as stream:
            while chunk := stream.read(1 << 20):
                read_bytes += len(chunk)
                if read_bytes > expected_size:
                    raise ValueError(f'{role}: excede la longitud de {release}')
                digest.update(chunk)
        if read_bytes != expected_size or digest.hexdigest() != expected_hash:
            raise ValueError(f'{role}: no coincide con la huella de la referencia {release}')
        checked[role] = dict(name=path.name, bytes=read_bytes, sha256=digest.hexdigest())
    return checked


def main():
    data = json.loads(PROFILES.read_text(encoding='ascii'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', choices=['native', *data['releases']],
                        help='native selecciona la release fijada para BMO-X2')
    parser.add_argument('directory', type=Path, help='Carpeta local de binarios originales')
    args = parser.parse_args()
    release = data['native_target_release'] if args.release == 'native' else args.release
    profile = data['releases'][release]
    try:
        files = verify(args.directory, release, profile)
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP: {error}\n')
    print(json.dumps(dict(schema=1, evidence='HOST: local firmware hash comparison',
                          family=data['family'], pci_id=data['pci_id'], release=release,
                          native_target_release=data['native_target_release'],
                          reference=profile['reference'], package_bytes=sum(f['bytes'] for f in files.values()),
                          files=files, gsp_boot_verified=False), indent=2))


if __name__ == '__main__':
    main()
