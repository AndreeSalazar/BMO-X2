"""Boot the DOOM arithmetic SBEF inside the single-page CASM ABI probe."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from doom_fixture import make_packet
from scope import ROOT, workspace
from wake import assemble, check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('sbef', type=Path)
    parser.add_argument('--qemu', default='C:/Program Files/qemu/qemu-system-x86_64.exe')
    args = parser.parse_args()
    reference = workspace(args.reference)
    if (reference / 'profile.txt').read_text(encoding='utf-8-sig').strip() != 'ring0-abi-probe-0.1':
        raise ValueError('Se requiere un run CASM del perfil ABI')
    check(reference)
    base_packet = (reference / 'INICIO.X86').read_bytes()
    sbef = args.sbef.read_bytes()
    packet, _ = make_packet(base_packet, sbef)

    run = reference.parent / f'run-doom-{uuid.uuid4().hex[:12]}'
    run.mkdir()
    (run / 'reference.x86').write_bytes(base_packet)
    (run / 'doom-fixed.sbef').write_bytes(sbef)
    (run / 'INICIO.X86').write_bytes(packet)
    (run / 'profile.txt').write_text('doom-abi-fixture\n', encoding='ascii')
    bridge = ROOT / 'kernel/boot/bridge'
    efi = run / 'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI'
    efi.parent.mkdir(parents=True)
    efi.write_bytes(assemble([bridge / name for name in ('cabecera.hex', 'entrada.hex', 'datos.hex', 'fuente.hex')]))
    disk_packet = run / 'build/Puente_Metal/METAL/INICIO.X86'
    disk_packet.parent.mkdir()
    disk_packet.write_bytes(packet)
    shell = shutil.which('powershell.exe')
    scripts = Path(__file__).resolve().parent
    subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(scripts / 'disk.ps1'),
                    '-OutputRoot', str(run), '-Programa', 'INICIO.X86', '-GPT'], check=True, timeout=60)
    subprocess.run([sys.executable, '-B', str(scripts / 'prepare.py'), '--workspace', str(run)],
                   check=True, timeout=30)
    qemu = str(Path(args.qemu).resolve())
    subprocess.run([sys.executable, '-B', str(scripts / 'probe.py'), '--workspace', str(run),
                    '--qemu', qemu, '--halt', '--abi-probe', '--doom-fixture'],
                   check=True, cwd=run, timeout=70)
    report = json.loads((run / 'build/puente-test-results.json').read_text(encoding='utf-8'))
    report.update(run=run.name, evidence='QEMU', milestone='DoomGeneric fixed arithmetic in CPL3')
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    (run / 'qemu-run.json').write_text(json.dumps(dict(cpu='qemu64', ram_mib=256)) + '\n', encoding='ascii')
    print(f'Run: {run}')


if __name__ == '__main__':
    main()
