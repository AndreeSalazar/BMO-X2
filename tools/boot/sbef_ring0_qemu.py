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

from casm_sbef_qemu import CHECKS, test_vectors, validate
from host.diagnostics import Rejection
from host.sbef.format import encode_header, inspect, load_plan
from host.toolchains.msvc import build_external_console, build_external_dll
from scope import ROOT, workspace
from bridge_hex import assemble
from fat32_read import Fat32


PAGES = 267
EXTERNAL_PAGES = 346
PEER_PAGES = 353
CONSOLE_PAGES = 347
CONSOLE_OUTPUT = b'Hola mundo desde C++ / MSVC en BMO-X2\r\n'
ALLOCATOR = ROOT / 'kernel/boot/bridge/desktop_media_alloc.S'
READER = ALLOCATOR.with_name('desktop_media_read.S')
PROBE = ROOT / 'kernel/loader/sbef_ring0_probe.S'
CLIENT = ROOT / 'tools/tests/sbef_external_client.S'
ATTESTED = ROOT / 'Reports/casm-sbef-freestanding-qemu.json'
REBASE_FIXTURE = ROOT / 'Reports/msvc-rebase-intake.json'


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


def stage(run, bridge, body, external=None):
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
        extra = ['--bmo-x2-folder', '--desktop', external] if external else []
        subprocess.run([sys.executable, '-B', tools / 'prepare.py', '--workspace', run, *extra],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)


def run_qemu(qemu, run, *, console=False):
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
    if console:
        command.extend(['-chardev', f'file,id=stdout,path={run / "stdout.log"}',
                        '-device', 'isa-debugcon,iobase=0xea,chardev=stdout'])
    with (run / 'qemu.log').open('wb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=45)
    lines = trace.read_text(encoding='ascii').splitlines()
    if result.returncode != 33:
        raise ValueError(f'QEMU termino con {result.returncode}: {lines}. Ver {run}')
    return lines


def external_bridge(bridge, reader):
    site, extension = 0x267, 0x3000
    if bridge[site:site+5] != bytes.fromhex('e894050000') or len(bridge) != extension or len(reader) > 4096:
        raise ValueError('El lector FAT32 excede el presupuesto del puente')
    struct.pack_into('<i', bridge, site+1, extension-site-5)
    old_path = ('\\METAL\\INICIO.X86' + '\0').encode('utf-16le')
    new_path = ('\\BMO-X2\\INICIO.X86' + '\0').encode('utf-16le')
    if bridge[0x1840:0x1840+len(old_path)] != old_path or len(new_path) > 0x40:
        raise ValueError('Cambio la ruta de entrada del puente')
    bridge[0x1840:0x1840+len(new_path)] = new_path
    for offset, old in ((0x5c, 0x2e00), (0x90, 0x4000), (0x150, 0x2e00), (0x158, 0x2e00)):
        if struct.unpack_from('<I', bridge, offset)[0] != old:
            raise ValueError('Cambio la cabecera PE del puente')
        struct.pack_into('<I', bridge, offset, old + 0x2000)
    return bridge + reader.ljust(8192, b'\0')


def external_image(code):
    base = 0x40000000
    data = bytearray(code)
    records = bytearray()
    for index in range(8):
        region = code if index == 0 else struct.pack('<I', index)
        if index == 7:
            region = region.ljust(4096, b'\0') + struct.pack('<I', 0x25121800)
        offset = 288 if index == 0 else 288 + len(data)
        records += struct.pack('<QIIIIQ', base + index * 8192, offset, len(region),
                               8192 if index == 7 else 4096,
                               5 if index == 0 else 4 + 2 * (index % 2 == 0), 0)
        if index:
            data += region
    return bytearray(encode_header(1, 8, 288 + len(data), base) + records + data)


def msvc_rebase_cases(executable, run):
    fixture = json.loads(REBASE_FIXTURE.read_bytes())
    source = executable.read_bytes()
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != fixture['SourceSHA256']:
        raise ValueError('El PE no coincide con la muestra MSVC auditada')
    output = run / 'msvc-rebase.sbef'
    verified_input = run / 'msvc-rebase.exe'
    verified_input.write_bytes(source)
    subprocess.run([sys.executable, '-B', ROOT / 'tools/sbef.py', 'pack', verified_input, output,
                    '--producer', 'msvc', '--abi', '1'], check=True, stdout=subprocess.DEVNULL)
    image = output.read_bytes()
    source_pointer = int(fixture['RelocationCheck']['SourcePointer'], 16)
    target_pointer = int(fixture['RelocationCheck']['SBEFPointer'], 16)
    target_rva = int(fixture['RelocationCheck']['TargetRVA'], 16)
    plan = load_plan(image)
    if plan['RegionCount'] != 4 or plan['Entry'] != 0x40001000:
        raise ValueError('El paquete MSVC ya no coincide con el perfil de cuatro regiones')
    data = next(region for region in plan['Regions'] if region['Permissions'] == 'RW')
    data_start = target_rva + 0x40000000 - data['VirtualStart']
    if not 0 <= data_start <= data['FileBytes'] - 8:
        raise ValueError('La relocacion no pertenece a los datos del ejecutable')
    pointer_offset = data['FileOffset'] + data_start
    if struct.unpack_from('<Q', image, pointer_offset)[0] != target_pointer:
        raise ValueError('HOST no escribio el puntero reubicado previsto')
    stale = bytearray(image)
    struct.pack_into('<Q', stale, pointer_offset, source_pointer)
    cases = (
        ('msvc-dir64', image, None, 0),
        ('msvc-stale-pointer', stale, f'SBEF CPL3 PF {source_pointer:016X}', 0),
    )
    return cases, dict(source_sha256=source_sha256, source_bytes=len(source),
                       source_pointer=f'0x{source_pointer:X}', target_pointer=f'0x{target_pointer:X}',
                       packaged_bytes=len(image), format_version=plan['FormatVersion'],
                       source_toolchain=fixture['Toolchain'])


def run_external(args, run, llvm, bridge, body, stream, module, extension=b''):
    bridge = external_bridge(bridge, assemble_stage(llvm, READER, run))
    rebase = None
    console = None
    dll_report = None
    if args.msvc_dll:
        image, dll_report = build_external_dll(ROOT, run, llvm / 'clang.exe')
        base = int(dll_report['LinkedModule']['ImageBase'], 16)
        writable = [region for region in load_plan(image)['Regions']
                    if region['VirtualStart'] >= base and region['Writable']]
        if len(writable) != 1:
            raise ValueError('La DLL de prueba debe tener una region RW propia')
        readonly = bytearray(image)
        struct.pack_into('<I', readonly, writable[0]['RecordOffset'] + 20, 4)
        cases = (
            ('msvc-dll', image, 'SBEF WIN64 EXIT 0000000000000000', 1),
            ('msvc-dll-readonly', readonly, f'SBEF CPL3 PF {writable[0]["VirtualStart"]:016X}', 0),
        )
    elif args.msvc_console:
        image, console = build_external_console(ROOT, run, llvm / 'clang.exe')
        calls = 6 + (len(CONSOLE_OUTPUT) + 7) // 8
        cases = (('msvc-console', image, 'SBEF WIN64 EXIT 0000000000000000', calls),)
    elif args.msvc_rebase:
        cases, rebase = msvc_rebase_cases(args.msvc_rebase, run)
    elif extension:
        signal = external_image(assemble_stage(llvm, CLIENT, run, BMO_EXTERNAL_PEER=1))
        isolated = external_image(assemble_stage(llvm, CLIENT, run, BMO_EXTERNAL_PEER=1,
                                                 BMO_EXTERNAL_PEER_FAULT=1))
        cases = (
            ('peer-signal', signal, 'SBEF CPL3 EXIT 0000000053424546', 5),
            ('peer-isolation', isolated, 'SBEF CPL3 PF 0000000040004004', 3),
        )
    else:
        normal = external_image(assemble_stage(llvm, CLIENT, run))
        fault = external_image(assemble_stage(llvm, CLIENT, run, BMO_EXTERNAL_FAULT=1))
        bad_stack = external_image(assemble_stage(llvm, CLIENT, run, BMO_EXTERNAL_BAD_STACK=1))
        bad_permissions, cpu, budget, abi = (bytearray(normal) for _ in range(4))
        struct.pack_into('<I', bad_permissions, 52, 7)
        struct.pack_into('<I', cpu, 24, 3)
        struct.pack_into('<I', budget, 32 + 7 * 32 + 16, 65 * 4096)
        struct.pack_into('<H', abi, 6, 0)
        cases = (
            ('exit', normal, 'SBEF CPL3 EXIT 0000000053424546', 14),
            ('fault', fault, 'SBEF CPL3 PF 0000000040002000', 14),
            ('bad-return-stack', bad_stack, 'SBEF ABI BAD RETURN 0000000000000000', 15),
            ('permissions', bad_permissions, None, 0),
            ('cpu', cpu, 'SBEF CPU UNSUPPORTED', 0),
            ('page-budget', budget, 'SBEF USER BUDGET', 0),
            ('abi', abi, 'SBEF ABI UNSUPPORTED', 0),
        )
    results = []
    for name, image, policy, calls in cases:
        receipt = 0
        pages = 0
        try:
            info = inspect(image)
        except Rejection as error:
            if name != 'permissions' or error.offset != 52:
                raise
            receipt = (1 + CHECKS.index((error.code, error.field))) * 2097152 + error.offset
        else:
            if name == 'permissions':
                raise ValueError('HOST admitio la muestra W+X')
            if calls or rebase or dll_report:
                plan = load_plan(image)
                pages = 1 + sum(region['PageCount'] for region in plan['Regions'])
                expected_regions, expected_pages = (6, 7) if dll_report else (
                    (4, 5) if rebase else (3, 5) if console else (8, 10))
                if info['AbiVersion'] != 1 or plan['RegionCount'] != expected_regions or pages != expected_pages:
                    raise ValueError('Cambio el contrato de la muestra externa')
        folder = run / ('run-' + name)
        folder.mkdir()
        payload = folder / 'fixture.sbef'
        payload.write_bytes(image)
        (folder / 'stream.bin').write_bytes(stream)
        stage(folder, bridge, body, payload)
        volume = Fat32(folder / 'build/puente-normal.img')
        try:
            if volume.file_bytes('BMO-X2/DESKTOP.SBF') != image:
                raise ValueError('El archivo SBEF de la imagen FAT32 difiere del fixture')
        finally:
            volume.close()
        observed = run_qemu(args.qemu.resolve(), folder, console=console is not None)
        expected = ['SBEF CPL0 POST-EBS', f'SBEF FAT32 BYTES {len(image):016X}', f'SBEF RECEIPT {receipt:016X}']
        if pages:
            expected.append(f'SBEF USER PAGES {pages:016X}')
        if name in ('fault', 'msvc-dll-readonly'):
            expected.append('SBEF PF ERROR 0000000000000007')
        if name in ('peer-isolation', 'msvc-stale-pointer'):
            expected.append('SBEF PF ERROR 0000000000000004')
        if name == 'msvc-dir64':
            counter_prefix = 'SBEF CPL3 REBASE COUNTER '
            counter = next((line for line in observed if line.startswith(counter_prefix)), '')
            if not counter or int(counter.removeprefix(counter_prefix), 16) <= 1:
                raise ValueError(f'MSVC no actualizo el dato desde CPL3. Ver {folder}')
            expected.append(counter)
        if policy:
            expected.append(policy)
        wakes = 0
        if rebase:
            expected.extend(['SBEF SYSCALLS 0000000000000000', 'SBEF WAIT WAKES 0000000000000000'])
        if calls or dll_report:
            expected.append(f'SBEF SYSCALLS {calls:016X}')
            wake_prefix = 'SBEF WAIT WAKES '
            wake_line = next((line for line in observed if line.startswith(wake_prefix)), '')
            wakes = int(wake_line.removeprefix(wake_prefix) or '0', 16)
            if (args.peer or dll_report) and wakes:
                raise ValueError(f'{name}: WAIT entro al bucle del PIT. Ver {folder}')
            if console and not 1 <= wakes <= 3:
                raise ValueError(f'{name}: WAIT debia despertar en uno a tres ticks. Ver {folder}')
            if not extension and not 1 <= wakes <= 2:
                raise ValueError(f'{name}: WAIT debia despertar en uno o dos ticks. Ver {folder}')
            expected.append(f'{wake_prefix}{wakes:016X}')
            if args.peer:
                peer_state = 2 if name == 'peer-signal' else 1
                expected.append(f'SBEF PEER STATE {peer_state:016X}')
            expected.append('SBEF ABI GATE RESTORED')
        if not pages:
            expected.append('SBEF REJECTED BEFORE USER MAP')
        staged_bytes = (len(image) + 4095) & -4096
        expected.extend([f'SBEF FAT32 SCRUBBED {staged_bytes:016X}', 'SBEF MAP RESTORED AND SCRUBBED'])
        if observed != expected:
            raise ValueError(f'{name}: recibos inesperados {observed}. Ver {folder}')
        if console:
            stdout = (folder / 'stdout.log').read_bytes()
            if stdout != CONSOLE_OUTPUT:
                raise ValueError(f'{name}: stdout inesperado {stdout!r}. Ver {folder}')
            console.update(stdout=stdout.decode('ascii'), stdout_bytes=len(stdout))
        results.append(dict(case=name, sha256=hashlib.sha256(image).hexdigest(), receipt=receipt,
                            user_pages=pages, syscalls=calls, wait_wakes=wakes, staging_bytes_scrubbed=staged_bytes,
                            trace=observed, passed=True))
        print(f'{name}: comprobado', flush=True)
    private_pages = PEER_PAGES if args.peer else CONSOLE_PAGES if console or dll_report else EXTERNAL_PAGES
    report = dict(run=run.name, evidence='QEMU/OVMF, SBEF from virtual FAT32 and real CPL3',
                  validator_text_sha256=module['text_sha256'], probe_sha256=hashlib.sha256(body).hexdigest(),
                  probe_bytes=len(body), private_pages=private_pages, user_frame_budget=64,
                  scratch_bytes_scrubbed=private_pages*4096, passed=len(results), cases=results)
    if args.peer:
        report.update(peer_extension_bytes=len(extension), peer_extension_sha256=hashlib.sha256(extension).hexdigest())
    if console or dll_report:
        report.update(extension_bytes=len(extension), extension_sha256=hashlib.sha256(extension).hexdigest())
    if console:
        report['msvc_console'] = console
    if dll_report:
        report['msvc_dll'] = dll_report
    if rebase:
        report['msvc_rebase'] = rebase
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module_run', type=Path)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument('--external', action='store_true', help='Read the SBEF from FAT32 and test CPL3')
    profiles.add_argument('--peer', action='store_true', help='Test WAIT with a second isolated CPL3 context')
    profiles.add_argument('--msvc-rebase', type=Path, metavar='EXE', help='Run the audited MSVC DIR64 fixture')
    profiles.add_argument('--msvc-console', action='store_true', help='Build and run the external Win64 console fixture')
    profiles.add_argument('--msvc-dll', action='store_true', help='Build and run the external EXE and DLL fixture')
    args = parser.parse_args()
    win64 = args.msvc_console or args.msvc_dll
    external = args.external or args.peer or win64 or args.msvc_rebase is not None
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
    if not external:
        stream += b''.join(struct.pack('<Q', len(payload)) + payload.ljust(296, b'\0')
                           for _, _, payload in cases)
    run = Path(tempfile.mkdtemp(prefix='run-sbef-ring0-', dir=ROOT / 'build/CASM'))
    print(f'Run: {run}', flush=True)
    llvm = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
    private_pages = PEER_PAGES if args.peer else CONSOLE_PAGES if win64 else EXTERNAL_PAGES if external else PAGES
    allocator = assemble_stage(llvm, ALLOCATOR, run, BMO_DMA_LAB_PAGES=private_pages)
    mode = dict(BMO_EXTERNAL_SBEF=1) if external else {}
    if args.peer:
        mode['BMO_EXTERNAL_PEER'] = 1
    if win64:
        mode['BMO_EXTERNAL_WIN64'] = 1
    if args.peer or win64:
        mode['BMO_EXTERNAL_EXT'] = 1
    if args.msvc_rebase:
        mode['BMO_EXTERNAL_REBASE'] = 1
    body = assemble_stage(llvm, PROBE, run, BMO_CASE_COUNT=len(cases), BMO_MODULE_ENTRY=module['entry'],
                          BMO_TRAP_ENTRY=module['trap_addresses']['bounds'], **mode)
    extension = b''
    if args.peer or win64:
        if not 4096 < len(body) <= 8192 or any(body[4072:4096]):
            raise ValueError('La extension de procesos excede su pagina o invade la cabecera del puente')
        extension = body[4096:]
        body = body[:4072]
        stream += extension.ljust(4096, b'\0')
    pieces = [ALLOCATOR.with_name(f'{part}.hex') for part in ('cabecera', 'entrada', 'datos', 'fuente')]
    bridge = bytearray(assemble(pieces))
    if not 0 < len(body) <= 4096 - 24 or not 0 < len(allocator) <= 0xf0:
        raise ValueError('La sonda excede el presupuesto del puente')
    if bridge[0x400:0x404] != bytes.fromhex('4883ec28'):
        raise ValueError('Cambio el punto de entrada del asignador')
    bridge[0x400:0x400+len(allocator)] = allocator
    if external:
        run_external(args, run, llvm, bridge, body, stream, module, extension)
        return
    (run / 'stream.bin').write_bytes(stream)
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
