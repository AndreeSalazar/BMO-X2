"""Arranca la sonda AMD-Vi/EDU en CPL0 tras ExitBootServices, solo en QEMU."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid

from scope import ROOT
from wake import assemble


PAGE_COUNT = 9
EFI_ALLOCATOR = ROOT / 'kernel/boot/bridge/desktop_media_alloc.S'
PROBE = ROOT / 'kernel/drivers/bus/amdvi/edu_probe.S'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code(llvm, source, folder, flags=()):
    obj = folder / (source.stem + '.o')
    raw = obj.with_suffix('.bin')
    subprocess.run([llvm / 'clang.exe', '--target=x86_64-unknown-none-elf',
                    f'-DBMO_DMA_LAB_PAGES={PAGE_COUNT}', *flags, '-c', source, '-o', obj], check=True)
    relocations = subprocess.check_output([llvm / 'llvm-objdump.exe', '-r', obj], text=True)
    if 'RELOCATION RECORDS' in relocations:
        raise ValueError(f'La sonda contiene relocaciones externas: {source.name}')
    subprocess.run([llvm / 'llvm-objcopy.exe', '-O', 'binary', '--only-section=.text', obj, raw], check=True)
    result = raw.read_bytes()
    raw.with_suffix('.hex').write_text('\n'.join(result[n:n + 16].hex(' ').upper()
                                               for n in range(0, len(result), 16)) + '\n', encoding='ascii')
    return result


def run_case(run, case, qemu, llvm, shell, bridge, allocator):
    folder = run / ('run-' + case)
    folder.mkdir()
    omit = case == 'omit-invalidation'
    body = code(llvm, PROBE, folder, ('-DBMO_DMA_OMIT_INVALIDATION',) if omit else ())
    if not 0 < len(body) <= 4096 - 24:
        raise ValueError('La sonda no cabe en el paquete de arranque')
    packet = b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body
    efi = folder / 'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI'
    efi.parent.mkdir(parents=True)
    efi.write_bytes(bridge)
    entry = folder / 'build/Puente_Metal/METAL/INICIO.X86'
    entry.parent.mkdir(parents=True)
    entry.write_bytes(packet)
    scripts = ROOT / 'tools/boot'
    with (folder / 'stage.log').open('w', encoding='utf-8') as log:
        subprocess.run([shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                        '-File', scripts / 'disk.ps1', '-OutputRoot', folder,
                        '-Programa', 'build/Puente_Metal/METAL/INICIO.X86', '-GPT'],
                       cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=30)
        subprocess.run([sys.executable, '-B', scripts / 'prepare.py', '--workspace', folder],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)

    share = qemu.parent / 'share'
    variables = folder / 'vars.fd'
    shutil.copyfile(share / 'edk2-i386-vars.fd', variables)
    serial = folder / 'serial.log'
    disk = folder / 'build/puente-normal.img'
    devices = ['-device', 'edu,addr=04.0', '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
    if case != 'missing-iommu':
        devices += ['-device', 'amd-iommu,dma-remap=on']
    command = [str(qemu), '-machine', 'q35', '-accel', 'tcg', '-cpu', 'qemu64', '-smp', '1', '-m', '256',
               '-display', 'none', '-monitor', 'none', '-no-reboot', '-nic', 'none', '-vga', 'std',
               '-drive', f'if=pflash,unit=0,format=raw,readonly=on,file={share / "edk2-x86_64-code.fd"}',
               '-drive', f'if=pflash,unit=1,format=raw,file={variables}',
               '-drive', f'file={disk},format=raw,if=ide,snapshot=on', '-serial', f'file:{serial}', *devices]
    with (folder / 'qemu.log').open('wb') as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=35)
        except subprocess.TimeoutExpired as error:
            latest = serial.read_text(errors='replace')[-1200:] if serial.exists() else ''
            raise RuntimeError(f'{case}: QEMU agoto el plazo; serie: {latest}') from error
    steps = [line.removeprefix('BMO DMA ') for line in serial.read_text(errors='replace').splitlines()
             if line.startswith('BMO DMA ')]
    expected = {
        'normal': (0x10, ['ENTER', 'GRANT', 'OUTSIDE', 'REVOKED', 'CLOSED', 'PASS']),
        'missing-iommu': (0x22, ['ENTER', 'FAIL 2']),
        'omit-invalidation': (0x26, ['ENTER', 'GRANT', 'OUTSIDE', 'STALE', 'CLOSED', 'FAIL 6']),
    }[case]
    if (result.returncode, steps) != ((expected[0] << 1) | 1, expected[1]):
        raise ValueError(f'{case}: salida {result.returncode}, etapas {steps}; ver {serial}')
    return dict(case=case, passed=True, steps=steps, probe_body_bytes=len(body),
                packet_sha256=digest(entry), bridge_sha256=digest(efi), allocator_bytes=len(allocator))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    args = parser.parse_args()
    qemu = args.qemu.resolve()
    if not qemu.is_file():
        parser.error('Falta QEMU')
    shell = shutil.which('powershell.exe')
    if not shell:
        parser.error('Falta Windows PowerShell')
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    run = ROOT / 'build/CASM' / ('run-amdvi-edu-' + uuid.uuid4().hex[:12])
    run.mkdir(parents=True)
    print(f'Run: {run}', flush=True)
    allocator = code(llvm, EFI_ALLOCATOR, run)
    paths = [EFI_ALLOCATOR.parent / f'{part}.hex' for part in ('cabecera', 'entrada', 'datos', 'fuente')]
    bridge = bytearray(assemble(paths))
    if not 0 < len(allocator) <= 0xf0 or bridge[0x400:0x404] != bytes.fromhex('4883ec28'):
        raise ValueError('El asignador excede el espacio del puente')
    bridge[0x400:0x400 + len(allocator)] = allocator
    cases = []
    for case in ('normal', 'missing-iommu', 'omit-invalidation'):
        result = run_case(run, case, qemu, llvm, shell, bridge, allocator)
        cases.append(result)
        print(f'{case}: {", ".join(result["steps"])}', flush=True)
    version = subprocess.check_output([qemu, '--version'], text=True).splitlines()[0]
    report = dict(schema=1, evidence='QEMU: guest CPL0 AMD-Vi with EDU after ExitBootServices',
                  run=run.name, qemu=version, scratch_bytes=PAGE_COUNT * 4096,
                  authorized_page_bytes=4096, test_transfer_bytes=8,
                  guest_probe_executed=True, physical_dma_verified=False, gpu_gsp_booted=False,
                  inputs={p.relative_to(ROOT).as_posix(): digest(p) for p in [*paths, EFI_ALLOCATOR, PROBE]},
                  cases=cases)
    (run / 'amdvi-edu-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(f'Informe: {run / "amdvi-edu-results.json"}')


if __name__ == '__main__':
    main()
