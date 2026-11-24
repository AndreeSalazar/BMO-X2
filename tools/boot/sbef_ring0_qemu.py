"""Boot the audited CASM Native validator in a guarded post-EBS QEMU profile."""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from casm_sbef_qemu import test_vectors, validate
from scope import ROOT, workspace
from bridge_hex import assemble


PAGES = 267
ALLOCATOR = ROOT / 'kernel/boot/bridge/desktop_media_alloc.S'
PROBE = ROOT / 'kernel/loader/sbef_ring0_probe.S'
ATTESTED = ROOT / 'Reports/casm-sbef-freestanding-qemu.json'


def assemble_stage(llvm, source, run, **defines):
    obj = run / (source.stem + '.o')
    raw = obj.with_suffix('.bin')
    subprocess.run([llvm / 'clang.exe', '--target=x86_64-unknown-none-elf',
                    *(f'-D{key}={value}' for key, value in defines.items()),
                    '-c', source, '-o', obj], check=True)
    if 'RELOCATION RECORDS' in subprocess.check_output([llvm / 'llvm-objdump.exe', '-r', obj], text=True):
        raise ValueError(f'Relocaciones externas en {source.name}')
    subprocess.run([llvm / 'llvm-objcopy.exe', '-O', 'binary', '--only-section=.text', obj, raw], check=True)
    return raw.read_bytes()


def stage(run, bridge, body):
    media = run / 'build/Puente_Metal'
    efi, entry = media / 'EFI/BOOT/BOOTX64.EFI', media / 'METAL/INICIO.X86'
    for path in (efi, entry):
        path.parent.mkdir(parents=True)
    efi.write_bytes(bridge)
    entry.write_bytes(b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body)
    tools = ROOT / 'tools/boot'
    with (run / 'stage.log').open('wb') as log:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                        '-File', tools / 'disk.ps1', '-OutputRoot', run,
                        '-Programa', 'build/Puente_Metal/METAL/INICIO.X86', '-GPT'],
                       cwd=run, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
        subprocess.run([sys.executable, '-B', tools / 'prepare.py', '--workspace', run],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)


def run_qemu(qemu, run):
    share = qemu.parent / 'share'
    variables = run / 'vars.fd'
    shutil.copyfile(share / 'edk2-i386-vars.fd', variables)
    trace = run / 'debug.log'
    disk, stream = run / 'build/puente-normal.img', run / 'stream.bin'
    command = [qemu, '-machine', 'pc', '-accel', 'tcg', '-cpu', 'qemu64', '-smp', '1', '-m', '256',
               '-display', 'none', '-monitor', 'none', '-no-reboot', '-nic', 'none',
               '-drive', f'if=pflash,unit=0,format=raw,readonly=on,file={share / "edk2-x86_64-code.fd"}',
               '-drive', f'if=pflash,unit=1,format=raw,file={variables}',
               '-drive', f'file={disk},format=raw,if=ide,snapshot=on',
               '-serial', f'file:{run / "serial.log"}', '-debugcon', f'file:{trace}',
               '-device', f'loader,file={stream},addr=0x02000000,force-raw=on',
               '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
    with (run / 'qemu.log').open('wb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=45)
    lines = trace.read_text(encoding='ascii').splitlines()
    if result.returncode != 33:
        raise ValueError(f'QEMU termino con {result.returncode}: {lines}. Ver {run}')
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module_run', type=Path)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    args = parser.parse_args()
    module = json.loads((workspace(args.module_run) / 'validator.module.json').read_bytes())
    validate(module)
    trusted = json.loads(ATTESTED.read_bytes())['freestanding']
    if any(module[field] != trusted[field] for field in ('text_sha256', 'data_sha256')):
        raise ValueError('El modulo no coincide con la evidencia del validador CASM')
    text, data = (bytes.fromhex(segment['hex']) for segment in module['segments'])
    if not (4096 < len(text) <= 8192 and len(data) == 2400 and module['entry'] == 0x4000f0):
        raise ValueError('El modulo no cabe en el perfil supervisor')
    expected, cases = test_vectors()
    stream = text.ljust(8192, b'\0') + data.ljust(4096, b'\0')
    stream += b''.join(struct.pack('<Q', len(payload)) + payload.ljust(296, b'\0')
                       for _, _, payload in cases)
    run = Path(tempfile.mkdtemp(prefix='run-sbef-ring0-', dir=ROOT / 'build/CASM'))
    print(f'Run: {run}', flush=True)
    (run / 'stream.bin').write_bytes(stream)
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    allocator = assemble_stage(llvm, ALLOCATOR, run, BMO_DMA_LAB_PAGES=PAGES)
    body = assemble_stage(llvm, PROBE, run, BMO_CASE_COUNT=len(cases), BMO_MODULE_ENTRY=module['entry'],
                          BMO_TRAP_ENTRY=module['trap_addresses']['bounds'])
    pieces = [ALLOCATOR.with_name(f'{part}.hex') for part in ('cabecera', 'entrada', 'datos', 'fuente')]
    bridge = bytearray(assemble(pieces))
    if not 0 < len(body) <= 4096 - 24 or not 0 < len(allocator) <= 0xf0:
        raise ValueError('La sonda excede el presupuesto del puente')
    if bridge[0x400:0x404] != bytes.fromhex('4883ec28'):
        raise ValueError('Cambio el punto de entrada del asignador')
    bridge[0x400:0x400+len(allocator)] = allocator
    stage(run, bridge, body)
    observed = run_qemu(args.qemu.resolve(), run)
    wanted = ['SBEF CPL0 POST-EBS', 'SBEF UD2 GUARD RX-WRITE NX-EXEC RECOVERED',
              *(f'SBEF RECEIPT {case["receipt"]:016X}' for case in expected),
              'SBEF MAP RESTORED AND SCRUBBED']
    if observed != wanted:
        raise ValueError(f'Los recibos Ring 0 difieren de HOST. Ver {run / "debug.log"}')
    report = dict(run=run.name, evidence='QEMU/OVMF, CPL0 after ExitBootServices',
                  module_text_sha256=module['text_sha256'], probe_sha256=hashlib.sha256(body).hexdigest(),
                  probe_bytes=len(body), private_pages=PAGES, module_data_pages=1,
                  recovered_traps=['#UD', '#PF guard', '#PF RX write', '#PF NX execute'], original_map_restored=True,
                  scratch_bytes_scrubbed=PAGES*4096, passed=len(expected), total=len(expected),
                  cases=expected)
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='ascii')
    print(f'Ring 0: {len(expected)} recibos comprobados y cuatro trampas recuperadas')


if __name__ == '__main__':
    main()
