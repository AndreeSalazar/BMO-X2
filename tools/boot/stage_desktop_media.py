"""Verify the desktop using a SBEF read from the boot volume by UEFI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid

from doom_fixture import make_packet, prepend_intro
from sbef_host.format import inspect
from scope import workspace
from stage_bmo_x2 import bridge_variant
from wake import SPLASH_PROFILE, check, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('abi_run', type=Path)
    parser.add_argument('splash_run', type=Path)
    parser.add_argument('desktop_run', type=Path)
    args = parser.parse_args()
    abi, splash, desktop = map(workspace, (args.abi_run, args.splash_run, args.desktop_run))
    for path, profile in ((abi, 'ring0-abi-probe-0.1'), (splash, SPLASH_PROFILE),
                          (desktop, 'desktop-external')):
        if (path / 'profile.txt').read_text(encoding='utf-8-sig').strip() != profile:
            parser.error(f'Se requiere {profile}')
    check(abi)
    check(splash)
    sbef = (desktop / 'desktop.sbef').read_bytes()
    regions = inspect(sbef)['Regions']
    if len(regions) != 3:
        parser.error('El escritorio requiere tres regiones')
    run = abi.parent / f'run-desktop-media-{uuid.uuid4().hex[:12]}'
    run.mkdir()
    scripts = Path(__file__).resolve().parent
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    for name in ('desktop_media_alloc', 'desktop_media_read', 'external_sbef', 'session_gate'):
        obj = run / f'{name}.o'
        source = scripts.parent / 'desktop/session_gate.S' if name == 'session_gate' else scripts / f'{name}.S'
        subprocess.run([llvm / 'clang.exe', '--target=x86_64-unknown-none-elf', '-DDESKTOP_MEDIA',
                        '-c', source, '-o', obj], check=True)
        subprocess.run([llvm / 'llvm-objcopy.exe', '-O', 'binary', '--only-section=.text',
                        obj, run / f'{name}.bin'], check=True)

    reference = (abi / 'INICIO.X86').read_bytes()
    intro = (splash / 'INICIO.X86').read_bytes()
    gate = (run / 'session_gate.bin').read_bytes()
    loader = (run / 'external_sbef.bin').read_bytes()
    packet, _ = make_packet(reference, sbef, session_gate=gate, external=loader)
    packet, _ = prepend_intro(packet, intro)
    for name, content in (('reference.x86', reference), ('desktop.sbef', sbef), ('session-gate.bin', gate),
                          ('external-loader.bin', loader), ('intro.x86', intro), ('INICIO.X86', packet),
                          ('intro.casm', (splash / 'source.casm').read_bytes()), ('profile.txt', b'desktop-media\n')):
        (run / name).write_bytes(content)

    image = bridge_variant()
    reader = (run / 'desktop_media_read.bin').read_bytes()
    site, extension = 0x267, 0x2800
    if image[site:site+5] != bytes.fromhex('e894050000') or any(image[extension:]) or len(reader) > len(image)-extension:
        raise ValueError('El lector ya no cabe en el puente')
    struct.pack_into('<i', image, site+1, extension-site-5)
    image[extension:extension+len(reader)] = reader
    allocator = (run / 'desktop_media_alloc.bin').read_bytes()
    if image[0x400:0x404] != bytes.fromhex('4883ec28') or len(allocator) > 0xf0:
        raise ValueError('Cambio la reserva de memoria del puente')
    image[0x400:0x400+len(allocator)] = allocator
    base = run / 'build/Puente_Metal'
    efi, payload = base / 'EFI/BOOT/BOOTX64.EFI', base / 'METAL/INICIO.X86'
    for path, data in ((efi, image), (payload, packet)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shell = shutil.which('powershell.exe')
    subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    scripts / 'disk.ps1', '-OutputRoot', run, '-Programa', 'INICIO.X86', '-GPT'],
                   check=True, timeout=60)
    rejected = bytearray(sbef)
    struct.pack_into('<I', rejected, 116, 7)
    bad = run / 'rejected.sbef'
    bad.write_bytes(rejected)
    for case, path in (('external-permissions', bad), ('normal', run / 'desktop.sbef')):
        subprocess.run([sys.executable, '-B', scripts / 'prepare.py', '--workspace', run,
                        '--bmo-x2-folder', '--desktop', path], check=True, timeout=30)
        if case != 'normal':
            (run / 'build/puente-normal.img').replace(run / 'build/puente-external-permissions.img')
    subprocess.run([sys.executable, '-B', scripts / 'probe.py', '--workspace', run, '--halt',
                    '--abi-probe', '--doom-fixture', '--ram-mib', '1024', '--casos', 'normal', 'external-permissions'],
                   check=True, cwd=run, timeout=100)

    media = run / 'media'
    files = {'EFI/BMO-X2/BMO-X2.EFI': efi, 'BMO-X2/INICIO.X86': payload,
             'BMO-X2/DESKTOP.SBF': run / 'desktop.sbef'}
    for name, src in files.items():
        target = media / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    report = json.loads((run / 'build/puente-test-results.json').read_text(encoding='utf-8'))
    report.update(run=run.name, evidence='QEMU', disk_sbef=True, physical_boot=False,
                  files={name: sha(media / name) for name in files})
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(f'Media: {media}')


if __name__ == '__main__':
    main()
