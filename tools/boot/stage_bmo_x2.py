"""Prepare and verify the named BMO-X2 EFI application in a virtual run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from scope import ROOT, workspace
from wake import HD_PROFILE, SPLASH_PROFILE, assemble, check


def bridge_variant(*, native_ui=False, nvidia_probe=False, gpu_preflight=False, gpu_mmio=False, gpu_fwsec=False):
    packet_path = r'\BMO-X2\INICIO.X86'
    if gpu_preflight:
        packet_path = r'\BMO-X2\GPU-PF\INICIO.X86'
    elif gpu_fwsec:
        packet_path = r'\BMO-X2\GPU-FW\INICIO.X86'
    elif gpu_mmio:
        packet_path = r'\BMO-X2\GPU-MM\INICIO.X86'
    elif nvidia_probe:
        packet_path = r'\BMO-X2\GPU\INICIO.X86'
    elif native_ui:
        packet_path = r'\BMO-X2\DESKTOP\INICIO.X86'
    missing_packet = 'RED [BMO-X2] no se pudo leer BMO-X2/INICIO.X86\r\n'
    if gpu_preflight:
        missing_packet = 'RED [BMO-X2] falta GPU-PF/INICIO.X86\r\n'
    elif gpu_fwsec:
        missing_packet = 'RED [BMO-X2] falta GPU-FW/INICIO.X86\r\n'
    elif gpu_mmio:
        missing_packet = 'RED [BMO-X2] falta GPU-MM/INICIO.X86\r\n'
    elif nvidia_probe:
        missing_packet = 'RED [BMO-X2] no se pudo leer BMO-X2/GPU/INICIO.X86\r\n'
    bridge = ROOT / 'kernel/boot/bridge'
    image = bytearray(assemble([bridge / name for name in
                                ('cabecera.hex', 'entrada.hex', 'datos.hex', 'fuente.hex')]))
    for offset, limit, old, new, encoding in (
        (0x1840, 0x1880, r'\METAL\INICIO.X86', packet_path, 'utf-16le'),
        (0x1980, 0x1a00, 'RED [METAL] no se pudo leer METAL/INICIO.X86\r\n',
         missing_packet, 'utf-16le'),
        (0x1b00, 0x1c00, 'Orquestador del Metal: cargando codigo propio...\r\n',
         'BMO-X2: cargando entrada CASM...\r\n', 'utf-16le'),
    ):
        original = (old + '\0').encode(encoding)
        replacement = (new + '\0').encode(encoding)
        if image[offset:offset + len(original)] != original or len(replacement) > limit - offset:
            raise ValueError('Cambio el bloque de texto del puente')
        image[offset:offset + max(len(original), len(replacement))] = replacement.ljust(
            max(len(original), len(replacement)), b'\0')
    if native_ui:
        # Presentation only. Preserve context signatures and all failure paths.
        # The CASM cat is the visual handoff; technical text stays in BOOTLOG.
        closed = b'METAL64: BootServices cerrados.\r\n\0'
        if image[0x1c00:0x1c00 + len(closed)] != closed:
            raise ValueError('Cambio el saludo del puente')
        image[0x1c00:0x1c00 + len(closed)] = bytes(len(closed))
        image[0x1b00:0x1c00] = bytes(0x100)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('splash_run', type=Path)
    args = parser.parse_args()
    source = workspace(args.splash_run)
    profile = (source / 'profile.txt').read_text(encoding='utf-8-sig').strip()
    if profile not in (SPLASH_PROFILE, HD_PROFILE):
        parser.error('Se requiere un run CASM del gato')
    check(source)
    run = source.parent / f'run-bmo-x2-{uuid.uuid4().hex[:12]}'
    run.mkdir()
    for name in ('INICIO.X86', 'source.casm', 'profile.txt'):
        shutil.copyfile(source / name, run / name)

    bridge = run / 'build/Puente_Metal'
    efi = bridge / 'EFI/BOOT/BOOTX64.EFI'
    efi.parent.mkdir(parents=True)
    image = bridge_variant()
    efi.write_bytes(image)
    packet = bridge / 'METAL/INICIO.X86'
    packet.parent.mkdir()
    shutil.copyfile(run / 'INICIO.X86', packet)
    scripts = Path(__file__).resolve().parent
    shell = shutil.which('powershell.exe')
    subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(scripts / 'disk.ps1'), '-OutputRoot', str(run), '-Programa', 'INICIO.X86', '-GPT'],
                   check=True, timeout=60)
    subprocess.run([sys.executable, '-B', str(scripts / 'prepare.py'), '--workspace', str(run),
                    '--bmo-x2-folder'], check=True, timeout=30)
    flags = ['--splash-hd'] if profile == HD_PROFILE else []
    subprocess.run([sys.executable, '-B', str(scripts / 'probe.py'), '--workspace', str(run),
                    '--halt', '--splash', '--ram-mib', '1024', *flags], check=True, timeout=60)

    staged = run / 'media'
    boot = staged / 'EFI/BMO-X2/BMO-X2.EFI'
    payload = staged / 'BMO-X2/INICIO.X86'
    boot.parent.mkdir(parents=True)
    payload.parent.mkdir()
    shutil.copyfile(efi, boot)
    shutil.copyfile(packet, payload)
    manifest = dict(evidence='QEMU', run=run.name, source=source.name, physical_boot=False,
                    files={p.relative_to(staged).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (boot, payload)})
    (staged / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
    print(f'Media: {staged}')


if __name__ == '__main__':
    main()
