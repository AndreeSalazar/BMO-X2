"""Comprueba los cuatro binarios de una release GSP GA10x en HOST."""

import argparse
import hashlib
import json
from pathlib import Path
import struct


PROFILES = Path(__file__).with_name('ga10x-firmware.json')
NATIVE_RELEASE = '615.78.08'
ELF_HEADER = struct.Struct('<16sHHIQQQIHHHHHH')
SECTION_HEADER = struct.Struct('<IIQQQQIIQQ')
GA10X_SECTIONS = (b'.fwimage', b'.fwversion', b'.fwsignature_ga10x')


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


def layout(image, release):
    if len(image)<ELF_HEADER.size:
        raise ValueError('GSP ELF: cabecera truncada')
    (ident, kind, machine, version, entry, phoff, shoff, flags, ehsize,
     _, phcount, shsize, count, names_index) = ELF_HEADER.unpack_from(image)
    if (ident[:7]!=b'\x7fELF\x02\x01\x01' or (kind,machine,version)!=(1,243,1)
            or entry or phoff or phcount or flags or ehsize!=ELF_HEADER.size):
        raise ValueError('GSP ELF: se esperaba un contenedor relocatable RISC-V de 64 bits')
    if (shsize!=SECTION_HEADER.size or not 1<=names_index<count<=128 or
            not ELF_HEADER.size<=shoff<=len(image)-count*shsize):
        raise ValueError('GSP ELF: tabla de secciones fuera de rango')

    def section(index):
        name, kind, _, _, offset, size, *_ = SECTION_HEADER.unpack_from(image,shoff+index*shsize)
        return name,kind,offset,size

    _, names_kind, names_offset, names_size = section(names_index)
    if names_kind!=3 or not ELF_HEADER.size<=names_offset<names_offset+names_size<=shoff:
        raise ValueError('GSP ELF: tabla de nombres invalida')
    names = bytes(image[names_offset:names_offset+names_size])
    sections = {}
    for index in range(1,count):
        name_offset, kind, offset, size = section(index)
        ending = names.find(b'\0',name_offset)
        if ending<0:
            raise ValueError('GSP ELF: nombre de seccion fuera de rango')
        name = names[name_offset:ending]
        if name not in GA10X_SECTIONS:
            continue
        if name in sections or kind!=1 or not ELF_HEADER.size<=offset<offset+size<=names_offset:
            raise ValueError(f'GSP ELF: seccion invalida o duplicada {name!r}')
        sections[name] = offset,size
    if sections.keys()!=set(GA10X_SECTIONS):
        raise ValueError('GSP ELF: falta imagen, version o firma GA10x')
    ordered = sorted(sections.values())
    if any(offset+size>next_offset for (offset,size),(next_offset,_) in zip(ordered,ordered[1:])):
        raise ValueError('GSP ELF: secciones GA10x solapadas')
    offset,size = sections[b'.fwversion']
    if image[offset:offset+size]!=release.encode('ascii')+b'\0':
        raise ValueError('GSP ELF: version interna distinta de la release')
    if sections[b'.fwsignature_ga10x'][1]!=4096:
        raise ValueError('GSP ELF: longitud inesperada de la firma GA10x')
    return dict(container='ELF64 RISC-V', internal_version=release,
                fwimage_pages_4k=(sections[b'.fwimage'][1]+4095)//4096,
                sections={name.decode('ascii'):dict(offset=offset,bytes=size,
                    sha256=hashlib.sha256(memoryview(image)[offset:offset+size]).hexdigest())
                          for name,(offset,size) in sections.items()})


def read_native_gsp(directory):
    profiles = json.loads(PROFILES.read_text(encoding='ascii'))
    info = verify(directory,NATIVE_RELEASE,profiles['releases'][NATIVE_RELEASE])['gsp']
    with (directory/info['name']).open('rb') as source:
        image = source.read(info['bytes']+1)
    if len(image)!=info['bytes'] or hashlib.sha256(image).hexdigest()!=info['sha256']:
        raise ValueError('GSP original cambio durante la lectura')
    return image,info


def main():
    data = json.loads(PROFILES.read_text(encoding='ascii'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', choices=['native', *data['releases']],
                        help='native selecciona la release fijada para BMO-X2')
    parser.add_argument('directory', type=Path, help='Carpeta local de binarios originales')
    parser.add_argument('--layout', action='store_true', help='Inventario de secciones del GSP de la release nativa')
    args = parser.parse_args()
    release = data['native_target_release'] if args.release == 'native' else args.release
    profile = data['releases'][release]
    if args.layout and release!=data['native_target_release']:
        parser.error('--layout solo admite la release nativa')
    try:
        files = verify(args.directory, release, profile)
        firmware_layout = {}
        if args.layout:
            gsp = files['gsp']
            with (args.directory/gsp['name']).open('rb') as stream:
                image = stream.read(gsp['bytes']+1)
            if len(image)!=gsp['bytes'] or hashlib.sha256(image).hexdigest()!=gsp['sha256']:
                raise ValueError('GSP cambio entre verificaciones')
            firmware_layout['gsp_layout'] = layout(image,release)
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP: {error}\n')
    print(json.dumps(dict(schema=1, evidence='HOST: local firmware hash comparison',
                          family=data['family'], pci_id=data['pci_id'], release=release,
                          native_target_release=data['native_target_release'],
                          reference=profile['reference'], package_bytes=sum(f['bytes'] for f in files.values()),
                          files=files, gsp_boot_verified=False, **firmware_layout), indent=2))


if __name__ == '__main__':
    main()
