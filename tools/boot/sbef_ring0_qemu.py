"""Boot the audited CASM Native validator in a guarded post-EBS QEMU profile."""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

from casm_sbef_qemu import CHECKS, test_vectors, validate
from host.diagnostics import Rejection
from host.sbef.format import encode_header, inspect, load_plan
from host.importers.pe_tls import TLS_BASES, TLS_STORAGE, TLS_VECTOR
from host.toolchains.msvc import build_external_console, build_external_crt, build_external_dll, build_external_tls
from scope import QEMU_SBEF_LIMIT, ROOT, workspace
from bridge_hex import assemble
from fat32_read import Fat32
from minigzip_fat import (
    FAT_HEADS, exhaust_pool, expected_torn_rollback, initial_image, output_layout,
    tear_interruption, verify_interruption, verify_output,
)


PAGES = 267
EXTERNAL_PAGES = 346
PEER_PAGES = 353
CONSOLE_PAGES = 347
TLS_PAGES = 348
BASE_USER_FRAMES = 64
PROCESS_USER_FRAMES = 96
PROCESS_PAGES = CONSOLE_PAGES + PROCESS_USER_FRAMES - BASE_USER_FRAMES
MINIGZIP_IO_LIMIT = 4096
GZIP_STAGING_TEST_BYTES = 65536
CONSOLE_OUTPUT = b'Hola mundo desde C++ / MSVC en BMO-X2\r\n'
PROCESS_OUTPUT = b'Win64 startup, last error, TLS and SList OK\r\n'
PROCESS_FLS_OUTPUT = b'FLS OK\r\n'
CRT_OUTPUT = b'MSVC CRT: inicio, main y cierre OK\r\n'
GS_HANDLER_OUTPUT = b'MSVC CRT: __GSHandlerCheck OK\r\n'
GS_UNWIND_OUTPUT = b'MSVC CRT: unwind de dos marcos OK\r\n'
GS_PROLOGUE_OUTPUT = b'MSVC CRT: epilogos RET y JMP detectados\r\n'
SEH_OUTPUT = {
    'cpu-seh-handled': b'MSVC SEH: filtro y __except OK\r\n',
    'cpu-seh-declined': b'MSVC SEH: filtro CONTINUE_SEARCH OK\r\n',
    'cpu-seh-outer': b'MSVC SEH: filtro del marco superior OK\r\n',
    'cpu-seh-finally': b'MSVC SEH: filtro, __finally, __except OK\r\n',
}
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
        extra = ['--bmo-x2-folder', '--desktop', external, '--qemu-sbef-media'] if external else []
        subprocess.run([sys.executable, '-B', tools / 'prepare.py', '--workspace', run, *extra],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)


def run_qemu(qemu, run, *, console=False, scratch_disk=None):
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
    if scratch_disk is not None:
        command.extend(['-drive', f'if=none,id=bmoscratch,file={scratch_disk},format=raw,cache=writethrough',
                        '-device', 'ide-hd,drive=bmoscratch,bus=ide.1,unit=0'])
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


def gzip_boundary_image(image):
    """Materialize zero-fill in RW without changing the guest memory contents."""
    data_region = load_plan(image)['Regions'][-1]
    padding = GZIP_STAGING_TEST_BYTES - len(image)
    if data_region['Permissions'] != 'RW' or not 0 < padding <= data_region['BssBytes']:
        raise ValueError('El SBEF GZIP no tiene relleno RW para comprobar el limite de carga')
    padded = bytearray(image) + bytes(padding)
    struct.pack_into('<I', padded, 12, len(padded))
    struct.pack_into('<I', padded, data_region['RecordOffset'] + 12, data_region['FileBytes'] + padding)
    return padded


def minigzip_cases(run, llvm, source):
    cases = []
    variants = {}
    for producer in ('msvc', 'clang-cl'):
        for role, argv, exit_code in (
            ('compress', ['-c', '-9', 'input.bin'], 0),
            ('decompress', ['-d', '-c'], 0),
            ('bad-crc', ['-d', '-c', 'input.bin'], 1),
            ('bad-args', ['-c', '-x'], 2),
        ):
            name = f'{producer}-minigzip-{role}'
            build = run / name
            build.mkdir()
            image, details = build_external_console(
                ROOT, build, llvm / 'clang.exe', gzip_source=source,
                use_clang=producer == 'clang-cl', minigzip_args=argv, corrupt_input=role == 'bad-crc')
            variants[name] = dict(details, mode=role, exit_code=exit_code)
            cases.append((name, image, f'SBEF WIN64 EXIT {exit_code:016X}', 1))
    return cases, variants


def minigzip_file_case(args, run, llvm):
    with args.input_file.open('rb') as source:
        data = source.read(MINIGZIP_IO_LIMIT + 1)
    if len(data) > MINIGZIP_IO_LIMIT:
        raise ValueError(f'La entrada excede {MINIGZIP_IO_LIMIT} bytes en el perfil minigzip')
    producer = args.minigzip_producer
    role = 'decompress' if args.decompress else 'compress'
    name = f'{producer}-minigzip-{role}'
    build = run / name
    build.mkdir()
    argv = ['-d', '-c'] if args.decompress else ['-c', f'-{args.level}']
    image, details = build_external_console(
        ROOT, build, llvm / 'clang.exe', gzip_source=args.msvc_minigzip,
        use_clang=producer == 'clang-cl', minigzip_args=argv, minigzip_input=data)
    return [(name, image, 'SBEF WIN64 EXIT 0000000000000000', 1)], {
        name: dict(details, mode=role, exit_code=0)}


def bounded_gzip(data):
    decoder = zlib.decompressobj(wbits=31)
    decoded = decoder.decompress(data, MINIGZIP_IO_LIMIT + 1)
    if len(decoded) > MINIGZIP_IO_LIMIT or not decoder.eof or decoder.unused_data:
        raise ValueError('Salida GZIP invalida, concatenada o fuera del presupuesto')
    return decoded


def publish_minigzip(output, data):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as file:
            temp = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.link(temp, output)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def minigzip_disk_cases(run, llvm, source, original, *, replacement=None):
    cases = []
    variants = {}
    fat = replacement is not None
    for producer, role in (('msvc', 'disk-write'), ('clang-cl', 'disk-read')):
        name = f'{producer}-minigzip-{role}'
        folder = run / name
        folder.mkdir()
        image, details = build_external_console(
            ROOT, folder, llvm / 'clang.exe', gzip_source=source, use_clang=producer == 'clang-cl',
            minigzip_args=[f'--{role}'], minigzip_input=original if role == 'disk-write' else b'',
            minigzip_disk=True, minigzip_fat=fat)
        variants[name] = dict(details, mode=role, exit_code=0)
        cases.append((name, image, 'SBEF WIN64 EXIT 0000000000000000', 1))
    negative = 'clang-cl-minigzip-disk-bad-crc'
    variants[negative] = dict(variants[name], mode='disk-bad-crc', exit_code=1)
    cases.append((negative, image, 'SBEF WIN64 EXIT 0000000000000001', 1))
    if fat:
        for mode in ('missing', 'cycle', 'exists'):
            writer = mode == 'exists'
            target = cases[0] if writer else cases[1]
            negative = f'{variants[target[0]]["producer"]}-minigzip-disk-{mode}'
            variants[negative] = dict(variants[target[0]], mode=f'disk-{mode}', exit_code=1)
            cases.append((negative, target[1], 'SBEF WIN64 EXIT 0000000000000001', 1))
        replace = 'msvc-minigzip-disk-replace'
        folder = run / replace
        folder.mkdir()
        image, details = build_external_console(
            ROOT, folder, llvm / 'clang.exe', gzip_source=source, minigzip_args=['--disk-replace'],
            minigzip_input=replacement, minigzip_disk=True, minigzip_fat=True)
        for name, role, payload, info, exit_code in (
            (replace, 'disk-replace', image, details, 0),
            ('clang-cl-minigzip-disk-read-replacement', 'disk-read-replacement',
             cases[1][1], variants[cases[1][0]], 0),
            ('msvc-minigzip-disk-no-space', 'disk-no-space', image, details, 1),
        ):
            variants[name] = dict(info, mode=role, exit_code=exit_code)
            cases.append((name, payload, f'SBEF WIN64 EXIT {exit_code:016X}', 1))
        for point in ('before', 'after'):
            name = f'msvc-minigzip-disk-cut-{point}'
            folder = run / name
            folder.mkdir()
            interrupted, details = build_external_console(
                ROOT, folder, llvm / 'clang.exe', gzip_source=source, minigzip_args=[f'--disk-cut-{point}'],
                minigzip_input=replacement, minigzip_disk=True, minigzip_fat=True)
            variants[name] = dict(details, mode=f'disk-cut-{point}', exit_code=3)
            cases.append((name, interrupted, 'SBEF WIN64 EXIT 0000000000000003', 1))
            recover = f'clang-cl-minigzip-disk-recover-{point}'
            variants[recover] = dict(variants[cases[1][0]], mode=f'disk-recover-{point}', exit_code=0)
            cases.append((recover, cases[1][1], 'SBEF WIN64 EXIT 0000000000000000', 1))
        for target, point, exit_code in (
            ('primary', 'before', 0), ('secondary', 'after', 0), ('fat', 'before', 0), ('both', 'before', 1),
            ('directory', 'after', 0), ('payload', 'after', 0), ('both-payloads', 'after', 1),
        ):
            name = f'clang-cl-minigzip-disk-torn-{target}'
            variants[name] = dict(variants[cases[1][0]], mode='disk-torn', point=point, target=target,
                                  exit_code=exit_code)
            cases.append((name, cases[1][1], f'SBEF WIN64 EXIT {exit_code:016X}', 1))
    return cases, variants


def run_external(args, run, llvm, bridge, body, stream, module, extension=b'', *, native_crt=None):
    bridge = external_bridge(bridge, assemble_stage(llvm, READER, run, BMO_QEMU_SBEF_MEDIA=1))
    rebase = None
    console = None
    crt_report = None
    dll_report = None
    tls_report = None
    cli = None
    disk_source = args.msvc_minigzip_disk or args.msvc_minigzip_fat
    disk_mode = disk_source is not None
    fat_mode = args.msvc_minigzip_fat is not None
    gzip_run = args.msvc_gzip or args.msvc_minigzip or disk_mode
    scratch_disk = None
    stopped_disks = {}
    recovered_disks = {}
    if args.msvc_tls:
        image, tls_report = build_external_tls(ROOT, run, llvm / 'clang.exe')
        second = next(region for region in load_plan(image)['Regions'] if region['VirtualStart'] == TLS_BASES[1])
        shared = bytearray(image)
        struct.pack_into('<Q', shared, second['FileOffset'] + TLS_VECTOR, TLS_BASES[0] + TLS_STORAGE)
        cases = (
            ('msvc-tls', image, 'SBEF WIN64 EXIT 0000000000000000', 2),
            ('msvc-tls-shared-control', shared, 'SBEF WIN64 EXIT 0000000000000001', 2),
        )
    elif args.msvc_dll or args.msvc_dll_lifecycle:
        lifecycle = args.msvc_dll_lifecycle
        image, dll_report = build_external_dll(ROOT, run, llvm / 'clang.exe', lifecycle=lifecycle)
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
        if lifecycle:
            refused = run / 'refused-attach'
            refused.mkdir()
            rejected, attach_report = build_external_dll(ROOT, refused, llvm / 'clang.exe',
                                                         lifecycle=True, reject_attach=True)
            if writable[0]['VirtualStart'] != 0x40803000:
                raise ValueError('Cambio la direccion del contador de la DLL')
            cases += (('msvc-dll-refused', rejected, 'SBEF WIN64 EXIT 0000000000000002', 1),)
            dll_report['RefusedAttachModule'] = attach_report['LinkedModule']
    elif disk_mode:
        original = (hashlib.shake_256(b'BMO-X2 FAT16 multi-cluster').digest(1280) + bytes(1792)
                    if fat_mode else bytes(range(256)) * 12)
        replacement = (hashlib.shake_256(b'BMO-X2 FAT16 replacement').digest(700) + bytes(2372)
                       if fat_mode else None)
        cases, cli = minigzip_disk_cases(run, llvm, disk_source, original, replacement=replacement)
        scratch_disk = run / 'minigzip-scratch.img'
        initial_disk = initial_image() if fat_mode else b'BMO QEMU scratch'.ljust(1024*1024, b'\0')
        scratch_disk.write_bytes(initial_disk)
    elif args.msvc_minigzip:
        cases, cli = (minigzip_file_case(args, run, llvm) if args.input_file
                      else minigzip_cases(run, llvm, args.msvc_minigzip))
    elif args.msvc_process:
        base_calls = 6 + (len(PROCESS_OUTPUT) + 7) // 8
        cases = []
        console = {}
        for producer, code, terminate in (('msvc', 0, False), ('clang-cl', 0xdeadbeef, False),
                                          ('msvc', 0x8000002a, True)):
            name = f'{producer}-process-{"terminate" if terminate else "start"}'
            build = run / name
            build.mkdir()
            image, details = build_external_console(
                ROOT, build, llvm / 'clang.exe', process_exit=code, use_clang=producer == 'clang-cl',
                terminate_process=terminate)
            calls = base_calls if terminate else base_calls + (len(PROCESS_FLS_OUTPUT) + 7) // 8
            cases.append((name, image, f'SBEF WIN64 EXIT {code:016X}', calls))
            console[name] = details
        over_budget = bytearray(cases[0][1])
        regions = load_plan(over_budget)['Regions']
        last = regions[-1]
        extra = PROCESS_USER_FRAMES + 1 - sum(region['PageCount'] for region in regions)
        struct.pack_into('<I', over_budget, last['RecordOffset'] + 16, last['MemoryBytes'] + extra * 4096)
        cases.append(('msvc-process-page-budget', over_budget, 'SBEF USER BUDGET', 0))
    elif args.msvc_console or args.msvc_heap or args.msvc_package_file or args.msvc_gzip:
        options = dict(heap=args.msvc_heap, package_file=args.msvc_package_file, gzip_source=args.msvc_gzip)
        image, console = build_external_console(ROOT, run, llvm / 'clang.exe', **options)
        calls = 6 + (len(CONSOLE_OUTPUT) + 7) // 8
        label = 'gzip' if args.msvc_gzip else 'package-file' if args.msvc_package_file else (
            'heap' if args.msvc_heap else 'console')
        cases = ((f'msvc-{label}', image, 'SBEF WIN64 EXIT 0000000000000000', calls),)
        if args.msvc_heap or args.msvc_package_file or args.msvc_gzip:
            clang_dir = run / 'clang-cl'
            clang_dir.mkdir()
            clang_image, clang_report = build_external_console(
                ROOT, clang_dir, llvm / 'clang.exe', use_clang=True, **options)
            console['clang_cl'] = clang_report
            cases += ((f'clang-cl-{label}', clang_image, 'SBEF WIN64 EXIT 0000000000000000', calls),)
        if args.msvc_gzip:
            cases += (('msvc-gzip-staging-limit', gzip_boundary_image(image),
                       'SBEF WIN64 EXIT 0000000000000000', calls),)
    elif args.msvc_crt or args.msvc_crt_gs or args.msvc_crt_gs_native:
        guarded = args.msvc_crt_gs or args.msvc_crt_gs_native
        image, crt_report = native_crt or build_external_crt(ROOT, run, llvm / 'clang.exe', guarded=guarded)
        calls = 1 + (len(CRT_OUTPUT) + 7) // 8
        name = 'msvc-crt-gs-native' if args.msvc_crt_gs_native else 'msvc-crt-gs' if guarded else 'msvc-crt'
        cases = ((name, image, 'SBEF WIN64 EXIT 0000000000000000', calls),)
        if guarded:
            address = crt_report['stack_cookie']['test_mode_address']
            regions = load_plan(image)['Regions']
            region = next(item for item in regions
                          if item['Writable'] and item['VirtualStart'] <= address
                          and address + 4 <= item['VirtualStart'] + item['FileBytes'])
            offset = region['FileOffset'] + address - region['VirtualStart']
            if struct.unpack_from('<I', image, offset) != (0x424d4f00,):
                raise ValueError('Cambio el selector /GS del fixture')
            controls = [('mismatch', 1, 'SBEF CPL3 ABORT 000000004753434B', 0)]
            if args.msvc_crt_gs_native:
                handler_calls = 1 + (len(GS_HANDLER_OUTPUT) + 7) // 8
                unwind_calls = 1 + (len(GS_UNWIND_OUTPUT) + 7) // 8
                prologue_calls = 1 + (len(GS_PROLOGUE_OUTPUT) + 7) // 8
                controls.extend((
                    ('handler', 2, 'SBEF WIN64 EXIT 0000000000000000', handler_calls),
                    ('handler-mismatch', 3, 'SBEF CPL3 ABORT 0000000047534844', 0),
                    ('cpu-exception', 4, 'SBEF WIN64 EXIT 0000000000000000', unwind_calls),
                    ('cpu-exception-mismatch', 5, 'SBEF CPL3 ABORT 0000000047534844', 0),
                    ('cpu-exception-repeat', 6, 'SBEF CPL3 ABORT 0000000047534455', 0),
                    ('cpu-prologue', 7, 'SBEF WIN64 EXIT 0000000000000000', prologue_calls),
                ))
                controls.extend(
                    (label, selector, 'SBEF WIN64 EXIT 0000000000000000', 1 + (len(stdout) + 7) // 8)
                    for selector, (label, stdout) in enumerate(SEH_OUTPUT.items(), 8)
                )
            for label, selector, terminal, count in controls:
                control = bytearray(image)
                struct.pack_into('<I', control, offset, 0x424d4f00 + selector)
                cases += ((name + '-' + label, control, terminal, count),)
            if args.msvc_crt_gs_native:
                exception = crt_report['cpu_exception']
                primary = exception['unwind_rvas']['call_client']
                fragment = exception['unwind_rvas']['chained_fragment']
                metadata_controls = (
                    ('unsupported-unwind', primary + 5, b'\x03', b'\x0f'),  # SET_FPREG -> unknown
                    ('invalid-chain', fragment + 16, struct.pack('<I', primary), struct.pack('<I', primary + 4)),
                    ('invalid-frame', fragment + 3, b'\x85', b'\x95'),  # inconsistent RBP offset
                )
                for label, rva, before, after in metadata_controls:
                    address = exception['image_base'] + rva
                    readonly = next(item for item in regions if not item['Writable'] and not item['Executable']
                                    and item['VirtualStart'] <= address
                                    and address + len(before) <= item['VirtualStart'] + item['FileBytes'])
                    at = readonly['FileOffset'] + address - readonly['VirtualStart']
                    if image[at:at + len(before)] != before:
                        raise ValueError(f'Cambio el metadato de control {label}')
                    control = bytearray(image)
                    control[at:at + len(before)] = after
                    struct.pack_into('<I', control, offset, 0x424d4f04)
                    cases += ((name + '-cpu-exception-' + label, control, 'SBEF WIN64 EXIT 0000000000000001', 1),)
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
    stdout_report = console or crt_report or cli
    results = []
    for name, image, policy, calls in cases:
        if len(image) > QEMU_SBEF_LIMIT:
            raise ValueError(f'{name}: SBEF de {len(image)} bytes supera el limite de {QEMU_SBEF_LIMIT}')
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
            if calls or rebase or dll_report or crt_report:
                plan = load_plan(image)
                pages = (2 if tls_report else 1) + sum(region['PageCount'] for region in plan['Regions'])
                if gzip_run:
                    valid_layout = ([region['Permissions'] for region in plan['Regions']] == ['RX', 'R', 'RW']
                                    and pages <= 64)
                elif args.msvc_heap or args.msvc_package_file:
                    valid_layout = plan['RegionCount'] == 3 and 23 <= pages <= 26
                elif args.msvc_process:
                    valid_layout = ([region['Permissions'] for region in plan['Regions']] == ['RX', 'R', 'RW']
                                    and BASE_USER_FRAMES + 1 < pages <= PROCESS_USER_FRAMES + 1
                                    and len(image) >= 236032)
                else:
                    expected_regions, expected_pages = (5, 7) if tls_report else (6, 7) if dll_report else (
                        (4, 5) if rebase else (3, 7) if args.msvc_crt_gs_native else (3, 4 if crt_report else 5)
                        if stdout_report else (8, 10))
                    valid_layout = plan['RegionCount'] == expected_regions and pages == expected_pages
                if info['AbiVersion'] != 1 or not valid_layout:
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
        active_disk = scratch_disk
        if disk_mode:
            disk_case = cli[name]
            disk_role = disk_case['mode']
            if disk_role in ('disk-replace', 'disk-read-replacement'):
                active_disk = run / 'minigzip-replaced.img'
                if disk_role == 'disk-replace':
                    active_disk.write_bytes(written_disk)
            elif disk_role.startswith(('disk-cut-', 'disk-recover-')):
                point = disk_role.rsplit('-', 1)[-1]
                active_disk = run / f'minigzip-interrupted-{point}.img'
                if disk_role.startswith('disk-cut-'):
                    active_disk.write_bytes(written_disk)
            elif disk_role == 'disk-torn':
                point = disk_case['point']
                active_disk = run / f'minigzip-torn-{disk_case["target"]}.img'
                torn_disk = tear_interruption(stopped_disks[point], disk_case['target'], replacement_chain,
                                              original=written_disk, final=replaced_disk)
                active_disk.write_bytes(torn_disk)
            elif cli[name]['exit_code']:
                negative_disk = bytearray(written_disk)
                if disk_role == 'disk-bad-crc':
                    crc_offset = len(compressed) - 8
                    physical = (offsets[crc_offset // 512] + crc_offset % 512
                                if fat_mode else data_offset + crc_offset)
                    negative_disk[physical] ^= 1
                elif disk_role == 'disk-missing':
                    entry, _, _, _ = output_layout(written_disk)
                    negative_disk[entry] = ord('X')
                elif disk_role == 'disk-cycle':
                    for head in FAT_HEADS:
                        struct.pack_into('<H', negative_disk, head + 2 * chain[0], chain[0])
                elif disk_role == 'disk-no-space':
                    negative_disk = exhaust_pool(written_disk)
                active_disk = run / f'minigzip-{disk_role}.img'
                active_disk.write_bytes(negative_disk)
        observed = run_qemu(args.qemu.resolve(), folder, console=stdout_report is not None,
                            scratch_disk=active_disk)
        if disk_mode:
            after_boot = active_disk.read_bytes()
            if disk_role == 'disk-write':
                if fat_mode:
                    compressed, chain, offsets = verify_output(initial_disk, after_boot)
                    data_offset = offsets[0]
                    calls = (9 + len(chain)) * 65 + 1
                else:
                    magic, size = struct.unpack_from('<4sI', after_boot, 512)
                    if magic != b'BMO1' or not 18 <= size <= 504:
                        raise ValueError(f'{name}: cabecera GZIP ausente del sector persistente. Ver {folder}')
                    data_offset = 520
                    compressed = after_boot[data_offset:data_offset+size]
                    if (after_boot[:512] != initial_disk[:512] or after_boot[1024:] != initial_disk[1024:]
                            or any(after_boot[data_offset+size:1024])):
                        raise ValueError(f'{name}: cambios fuera del registro persistente. Ver {folder}')
                    calls = 66
                if bounded_gzip(compressed) != original:
                    raise ValueError(f'{name}: sector persistido invalido. Ver {folder}')
                written_disk = after_boot
            elif disk_role == 'disk-replace':
                updated, replacement_chain, _ = verify_output(written_disk, after_boot, replaced=True)
                if bounded_gzip(updated) != replacement:
                    raise ValueError(f'{name}: reemplazo distinto de la referencia. Ver {folder}')
                replaced_disk = after_boot
                calls = (15 + 2 * len(replacement_chain) + len(chain)) * 65 + 1
            elif disk_role == 'disk-read-replacement':
                if after_boot != replaced_disk:
                    raise ValueError(f'{name}: la lectura modifico el reemplazo. Ver {folder}')
                calls = (6 + len(replacement_chain)) * 65 + 1 + (len(replacement) + 7) // 8
            elif disk_role.startswith('disk-cut-'):
                committed = disk_role.endswith('-after')
                stopped_disks[point] = after_boot
                recovered_disks[point] = verify_interruption(
                    written_disk, replaced_disk, after_boot, committed=committed)
                calls = ((11 if committed else 9) + 2 * len(replacement_chain) + len(chain)) * 65 + 1
            elif disk_role == 'disk-torn' and disk_case['exit_code']:
                if after_boot != torn_disk:
                    raise ValueError(f'{name}: el rechazo del diario altero el disco. Ver {folder}')
                reads = len(chain) + len(replacement_chain) if disk_case['target'] == 'both-payloads' else 0
                calls = (6 + reads) * 65 + 1
            elif disk_role.startswith('disk-recover-') or disk_role == 'disk-torn':
                damaged = disk_case.get('target')
                rollback = damaged in ('directory', 'payload')
                expected_disk = (expected_torn_rollback(written_disk, replaced_disk, torn_disk) if rollback
                                 else recovered_disks[point])
                if after_boot != expected_disk:
                    raise ValueError(f'{name}: la recuperacion dejo cambios inesperados. Ver {folder}')
                recovered_chain = replacement_chain if point == 'after' and not rollback else chain
                extra = int(rollback) + (len(replacement_chain) if damaged == 'payload' else 0)
                calls = (10 + 2 * len(recovered_chain) + extra) * 65 + 1 + (len(original) + 7) // 8
            elif disk_role == 'disk-read':
                if after_boot != written_disk:
                    raise ValueError(f'{name}: la lectura modifico el disco. Ver {folder}')
                calls = ((6 + len(chain)) * 65 + 1 if fat_mode else 3 + (len(compressed) + 7) // 8)
                calls += (len(original) + 7) // 8
            else:
                if after_boot != negative_disk:
                    raise ValueError(f'{name}: el rechazo modifico el disco. Ver {folder}')
                calls = ((6 + (len(chain) if disk_role == 'disk-bad-crc' else 0)) * 65 + 1
                         if fat_mode else 3 + (len(compressed) + 7) // 8)
        elif gzip_run:
            output_bytes = (folder / 'stdout.log').stat().st_size
            failed_cli = cli is not None and cli[name]['exit_code'] != 0
            minimum = 0 if cli is not None and cli[name]['mode'] == 'decompress' else 18
            if (failed_cli and output_bytes != 0) or (not failed_cli and
                    not minimum <= output_bytes <= MINIGZIP_IO_LIMIT):
                exit_receipt = next((line for line in observed if line.startswith('SBEF WIN64 EXIT ')), '')
                raise ValueError(f'{name}: {output_bytes} bytes de stdout {exit_receipt}. Ver {folder / "debug.log"}')
            calls = 1 + (output_bytes + 7) // 8
        expected = ['SBEF CPL0 POST-EBS', f'SBEF FAT32 BYTES {len(image):016X}', f'SBEF RECEIPT {receipt:016X}']
        if pages:
            expected.append(f'SBEF USER PAGES {pages:016X}')
        if '-cpu-exception' in name or '-cpu-seh-' in name:
            expected.append('SBEF WIN64 #UD DELIVERED')
        if name.endswith('-cpu-prologue'):
            expected.append('SBEF WIN64 #UD PROLOGUE DELIVERED')
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
        if args.msvc_dll_lifecycle and calls:
            expected.append('SBEF DLL COUNTER CLEARED')
        if tls_report:
            expected.append('SBEF TLS THREAD SWITCH')
        if policy:
            expected.append(policy)
        wakes = 0
        if rebase:
            expected.extend(['SBEF SYSCALLS 0000000000000000', 'SBEF WAIT WAKES 0000000000000000'])
        if calls or dll_report or crt_report:
            expected.append(f'SBEF SYSCALLS {calls:016X}')
            wake_prefix = 'SBEF WAIT WAKES '
            wake_line = next((line for line in observed if line.startswith(wake_prefix)), '')
            wakes = int(wake_line.removeprefix(wake_prefix) or '0', 16)
            if (args.peer or dll_report or tls_report or crt_report) and wakes:
                raise ValueError(f'{name}: WAIT entro al bucle del PIT. Ver {folder}')
            if gzip_run and wakes:
                raise ValueError(f'{name}: WAIT inesperado. Ver {folder}')
            if args.msvc_process and not 0 <= wakes <= 2:
                raise ValueError(f'{name}: WAIT excedio dos ticks del PIT. Ver {folder}')
            if console and not (args.msvc_gzip or args.msvc_process) and not 1 <= wakes <= 3:
                raise ValueError(f'{name}: WAIT debia despertar en uno a tres ticks. Ver {folder}')
            if not extension and not 1 <= wakes <= 2:
                raise ValueError(f'{name}: WAIT debia despertar en uno o dos ticks. Ver {folder}')
            expected.append(f'{wake_prefix}{wakes:016X}')
            if args.peer:
                peer_state = 2 if name == 'peer-signal' else 1
                expected.append(f'SBEF PEER STATE {peer_state:016X}')
            if tls_report:
                expected.append('SBEF TLS GS BASE RESTORED')
            expected.append('SBEF ABI GATE RESTORED')
        if not pages:
            expected.append('SBEF REJECTED BEFORE USER MAP')
        staged_bytes = (len(image) + 4095) & -4096
        expected.extend([f'SBEF FAT32 SCRUBBED {staged_bytes:016X}', 'SBEF MAP RESTORED AND SCRUBBED'])
        if observed != expected:
            raise ValueError(f'{name}: recibos inesperados {observed}. Ver {folder}')
        if stdout_report is not None:
            stdout = (folder / 'stdout.log').read_bytes()
            if '-cpu-seh-' in name:
                label = name.removeprefix('msvc-crt-gs-native-')
                expected_stdout = SEH_OUTPUT[label]
            elif name.endswith('-cpu-exception'):
                expected_stdout = GS_UNWIND_OUTPUT
            elif name.endswith('-cpu-prologue'):
                expected_stdout = GS_PROLOGUE_OUTPUT
            elif name.endswith(('-unsupported-unwind', '-invalid-chain', '-invalid-frame')):
                expected_stdout = b''
            elif name.endswith('-handler'):
                expected_stdout = GS_HANDLER_OUTPUT
            elif args.msvc_process:
                expected_stdout = b'' if not calls else (
                    PROCESS_OUTPUT if name.endswith('-terminate') else PROCESS_OUTPUT + PROCESS_FLS_OUTPUT)
            elif cli is not None:
                scenario = cli[name]
                if disk_mode:
                    if disk_role == 'disk-torn' and not disk_case['exit_code']:
                        reference = (replacement if point == 'after' and disk_case['target'] == 'secondary'
                                     else original)
                    else:
                        reference = {
                            'disk-read': original, 'disk-read-replacement': replacement,
                            'disk-recover-before': original, 'disk-recover-after': replacement,
                        }.get(disk_role, b'')
                elif args.input_file:
                    original = (run / name / 'input.bin').read_bytes()
                    reference = bounded_gzip(original) if args.decompress else original
                else:
                    reference = b'' if scenario['exit_code'] else (run / name / 'expected-output.bin').read_bytes()
                actual = bounded_gzip(stdout) if scenario['mode'] == 'compress' else stdout
                if actual != reference:
                    raise ValueError(f'{name}: salida distinta de Windows. Ver {folder}')
                expected_stdout = None
            elif args.msvc_gzip:
                build_dir = run / 'clang-cl' if name.startswith('clang-cl-') else run
                expected_decoded = (build_dir / 'expected-output.bin').read_bytes()
                decoded = gzip.decompress(stdout)
                if decoded != expected_decoded or len(stdout) >= len(decoded):
                    raise ValueError(f'{name}: el GZIP del invitado difiere de la referencia. Ver {folder}')
                expected_stdout = None
            else:
                expected_stdout = (CRT_OUTPUT if crt_report else CONSOLE_OUTPUT) if calls else b''
            if expected_stdout is not None and stdout != expected_stdout:
                raise ValueError(f'{name}: stdout inesperado {stdout!r}. Ver {folder}')
            if '-cpu-seh-' in name:
                crt_report.setdefault('seh_fixture', {})[label] = stdout.decode('ascii')
            elif name.endswith('-cpu-exception'):
                crt_report['cpu_exception']['stdout'] = stdout.decode('ascii')
                crt_report['cpu_exception']['unwound_frames'] = 2
                crt_report['cpu_exception']['handler_context'] = {
                    'flags': 'CONTEXT_FULL',
                    'exception': 'EXCEPTION_ILLEGAL_INSTRUCTION',
                    'verified': ['RAX', 'RCX', 'RDX', 'R8', 'R9', 'R10', 'R11', 'CF', 'CS', 'SS', 'XMM0', 'XMM6'],
                }
                crt_report['cpu_exception']['verified_registers'] = ['RBX', 'RBP', 'RSI', 'RDI', 'R12', 'RSP', 'RIP', 'XMM6']
                crt_report['cpu_exception']['dynamic_stack_bytes'] = 64
                crt_report['cpu_exception']['unwind_operations'] = [
                    'UWOP_ALLOC_SMALL', 'UWOP_PUSH_NONVOL', 'UWOP_ALLOC_LARGE',
                    'UWOP_SAVE_NONVOL', 'UWOP_SAVE_XMM128', 'UWOP_SET_FPREG', 'UNW_FLAG_CHAININFO',
                ]
            elif name.endswith('-cpu-prologue'):
                crt_report['cpu_exception']['prologue_stdout'] = stdout.decode('ascii')
                crt_report['cpu_exception']['prologue_before_frame_pointer'] = True
                crt_report['cpu_exception']['epilogue_simulated'] = [
                    'ADD RSP', 'LEA RSP from RBP', 'POP/RET suffix', 'RIP-relative indirect tail JMP',
                ]
                crt_report['cpu_exception']['automatic_epilogue_detection'] = True
                crt_report['cpu_exception']['failed_detection_preserved_context'] = True
                crt_report['cpu_exception']['epilogue_stack_overrun_rejected'] = True
            elif name.endswith('-unsupported-unwind'):
                crt_report['cpu_exception']['unsupported_unwind_rejected'] = True
            elif name.endswith('-invalid-chain'):
                crt_report['cpu_exception']['invalid_chain_rejected'] = True
            elif name.endswith('-invalid-frame'):
                crt_report['cpu_exception']['invalid_frame_rejected'] = True
            elif name.endswith(('-cpu-exception-mismatch', '-cpu-exception-repeat')):
                control = name.rsplit('-', 1)[-1]
                crt_report['cpu_exception'][control + '_stdout_bytes'] = len(stdout)
            elif name.endswith('-handler'):
                crt_report['dispatch_fixture']['stdout'] = stdout.decode('ascii')
            elif name.endswith('-handler-mismatch'):
                crt_report['dispatch_fixture']['mismatch_stdout_bytes'] = len(stdout)
            elif args.msvc_process:
                if calls:
                    console[name].update(stdout=stdout.decode('ascii'), stdout_bytes=len(stdout),
                                         oversized_exit_rejected=True, dynamic_tls_slots=64,
                                         dynamic_tls_reuse_verified=True, slist_header_bytes=16,
                                         fls_slots=128, fls_free_callback_verified=True,
                                         fls_exit_callback_verified=not name.endswith('-terminate'),
                                         terminate_skipped_fls_callback=name.endswith('-terminate'),
                                         large_readonly_tail_verified=True,
                                         critical_section_recursion_verified=True,
                                         environment_snapshots_verified=True,
                                         utf8_utf16_conversion_verified=True,
                                         performance_counter_verified=True, processor_features_verified=True,
                                         main_image_path_verified=True, standard_handle_slots_verified=True,
                                         sbef_bytes=len(image), sbef_limit_bytes=QEMU_SBEF_LIMIT)
            elif cli is not None:
                scenario.update(stdout_bytes=len(stdout), stdout_sha256=hashlib.sha256(stdout).hexdigest())
            elif args.msvc_gzip:
                build_report = console['clang_cl'] if name.startswith('clang-cl-') else console
                build_report.update(stdout_sha256=hashlib.sha256(stdout).hexdigest(), stdout_bytes=len(stdout))
            elif calls:
                stdout_report.update(stdout=stdout.decode('ascii'), stdout_bytes=len(stdout))
            else:
                crt_report['stack_cookie']['mismatch_stdout_bytes'] = len(stdout)
        results.append(dict(case=name, sha256=hashlib.sha256(image).hexdigest(), receipt=receipt,
                            user_pages=pages, syscalls=calls, wait_wakes=wakes, staging_bytes_scrubbed=staged_bytes,
                            trace=observed, passed=True))
        if args.msvc_gzip:
            results[-1].update(decoded_bytes=len(decoded), decoded_sha256=hashlib.sha256(decoded).hexdigest(),
                               compressed_bytes=len(stdout), compressed_sha256=hashlib.sha256(stdout).hexdigest(),
                               sbef_bytes=len(image), sbef_limit_bytes=QEMU_SBEF_LIMIT,
                               corrupt_crc_rejected=True, scratch_file_round_trip=True,
                               scratch_file_limit_rejected=True, scratch_file_truncated=True,
                               package_enumeration_verified=True, file_delete_sharing_verified=True,
                               scratch_delete_verified=True)
        print(f'{name}: comprobado', flush=True)
    private_pages = TLS_PAGES if tls_report else PEER_PAGES if args.peer else (
        PROCESS_PAGES if args.msvc_process else CONSOLE_PAGES if stdout_report or dll_report else EXTERNAL_PAGES)
    report = dict(run=run.name, evidence='QEMU/OVMF, SBEF from virtual FAT32 and real CPL3',
                  validator_text_sha256=module['text_sha256'], probe_sha256=hashlib.sha256(body).hexdigest(),
                  probe_bytes=len(body), private_pages=private_pages,
                  user_frame_budget=PROCESS_USER_FRAMES if args.msvc_process else BASE_USER_FRAMES,
                  scratch_bytes_scrubbed=private_pages*4096, passed=len(results), cases=results)
    if args.peer:
        report.update(peer_extension_bytes=len(extension), peer_extension_sha256=hashlib.sha256(extension).hexdigest())
    if stdout_report or dll_report or tls_report:
        report.update(extension_bytes=len(extension), extension_sha256=hashlib.sha256(extension).hexdigest())
    if console:
        key = 'win64_process_start' if args.msvc_process else 'win64_gzip' if args.msvc_gzip else (
            'win64_package_file' if args.msvc_package_file else
            'win64_heap' if args.msvc_heap else 'msvc_console')
        report[key] = console
    if cli is not None:
        report['win64_minigzip_cli'] = cli
    if disk_mode:
        report['win64_minigzip_disk'] = dict(
            disk=scratch_disk.name, lba=data_offset // 512, sector_bytes=512, gzip_bytes=len(compressed),
            gzip_sha256=hashlib.sha256(compressed).hexdigest(), original_bytes=len(original),
            original_sha256=hashlib.sha256(original).hexdigest(), other_sectors_unchanged=True,
            read_only_boot_preserved_disk=True, corrupt_crc_rejected=True)
        if fat_mode:
            report['win64_minigzip_disk'].update(filesystem='FAT16', file='OUTPUT.GZ',
                                               directory_lba=65, cluster_chain=chain,
                                               data_lbas=[offset // 512 for offset in offsets],
                                               new_directory_entry=True, fat_copies_verified=True,
                                               missing_filename_rejected=True, cycle_rejected=True,
                                               existing_filename_preserved=True,
                                               recovery=dict(journal_lbas=[78, 79], interrupted_mirror_rolled_back=True,
                                                             published_replacement_recovered=True,
                                                             both_journal_copies_cleared=True,
                                                             torn_primary_recovered=True, torn_secondary_recovered=True,
                                                             torn_fat_link_recovered=True,
                                                             both_journal_copies_torn_rejected=True,
                                                             torn_directory_rolled_back=True,
                                                             torn_payload_rolled_back=True,
                                                             both_payloads_torn_rejected=True),
                                               replacement=dict(
                                                   cluster_chain=replacement_chain, gzip_bytes=len(updated),
                                                   sha256=hashlib.sha256(replacement).hexdigest(),
                                                   old_clusters_released=True, no_space_preserved_disk=True))
    if crt_report:
        report['msvc_crt'] = crt_report
    if dll_report:
        report['msvc_dll'] = dll_report
    if tls_report:
        report['msvc_tls'] = tls_report
    if rebase:
        report['msvc_rebase'] = rebase
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='ascii')
    if args.output_file:
        publish_minigzip(args.output_file, stdout)
        print(f'Archivo generado: {args.output_file}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module_run', type=Path)
    parser.add_argument('--qemu', type=Path, default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument('--external', action='store_true', help='Read the SBEF from FAT32 and test CPL3')
    profiles.add_argument('--peer', action='store_true', help='Test WAIT with a second isolated CPL3 context')
    profiles.add_argument('--msvc-rebase', type=Path, metavar='EXE', help='Run the audited MSVC DIR64 fixture')
    profiles.add_argument('--msvc-console', action='store_true', help='Build and run the external Win64 console fixture')
    profiles.add_argument('--msvc-process', action='store_true', help='Run the UTF-16 and DWORD Win64 startup fixture')
    profiles.add_argument('--msvc-heap', action='store_true', help='Run the Win64 process heap with MSVC and clang-cl')
    profiles.add_argument('--msvc-package-file', action='store_true',
                          help='Run the Win64 read-only package file with MSVC and clang-cl')
    profiles.add_argument('--msvc-gzip', type=Path, metavar='ZLIB_SOURCE',
                          help='Decode and compress gzip in CPL3 with zlib built by MSVC and clang-cl')
    profiles.add_argument('--msvc-minigzip', type=Path, metavar='ZLIB_SOURCE',
                          help='Run the adapted minigzip command line in Win64 CPL3')
    profiles.add_argument('--msvc-minigzip-disk', type=Path, metavar='ZLIB_SOURCE',
                          help='Persist GZIP to a separate virtual disk and read it after reboot')
    profiles.add_argument('--msvc-minigzip-fat', type=Path, metavar='ZLIB_SOURCE',
                          help='Create and reload a multi-cluster OUTPUT.GZ in a FAT16 virtual disk')
    parser.add_argument('--input-file', type=Path, help='Package one local minigzip input file')
    parser.add_argument('--output-file', type=Path, help='Save verified guest output to a new local file')
    parser.add_argument('--minigzip-producer', choices=('msvc', 'clang-cl'))
    parser.add_argument('--decompress', action='store_true', help='Decode the local GZIP input')
    parser.add_argument('--level', type=int, choices=range(1, 10), help='Compression level for a local input')
    profiles.add_argument('--msvc-crt', action='store_true', help='Test selected static UCRT functions in a Win64 process')
    profiles.add_argument('--msvc-crt-gs', action='store_true', help='Test MSVC /GS success and fail-fast in CPL3')
    profiles.add_argument('--msvc-crt-gs-native', action='store_true',
                          help='Test MSVC /GS with Microsoft libcmt and static UCRT in the abort-only probe')
    profiles.add_argument('--msvc-dll', action='store_true', help='Build and run the external EXE and DLL fixture')
    profiles.add_argument('--msvc-dll-lifecycle', action='store_true', help='Test attach, detach and refused attach')
    profiles.add_argument('--msvc-tls', action='store_true', help='Test the static Win64 TLS template on two CPL3 threads')
    args = parser.parse_args()
    if args.input_file or args.output_file or args.minigzip_producer or args.decompress or args.level:
        if not (args.msvc_minigzip and args.input_file and args.output_file):
            parser.error('El modo de archivo exige --msvc-minigzip, --input-file y --output-file')
        if args.decompress and args.level is not None:
            parser.error('--level se aplica solo a la compresion')
        if not args.input_file.is_file() or not args.output_file.parent.is_dir():
            parser.error('Se requiere un archivo de entrada y una carpeta de salida existentes')
        if os.path.lexists(args.output_file):
            parser.error('La ruta de salida ya existe')
        args.level = args.level or 6
        args.minigzip_producer = args.minigzip_producer or 'msvc'
    win64 = (args.msvc_console or args.msvc_process or args.msvc_heap or args.msvc_package_file or args.msvc_gzip or args.msvc_minigzip
             or args.msvc_minigzip_disk or args.msvc_minigzip_fat
             or args.msvc_crt
             or args.msvc_crt_gs or args.msvc_crt_gs_native or args.msvc_dll
             or args.msvc_dll_lifecycle or args.msvc_tls)
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
    private_pages = TLS_PAGES if args.msvc_tls else PEER_PAGES if args.peer else (
        PROCESS_PAGES if args.msvc_process else CONSOLE_PAGES if win64 else EXTERNAL_PAGES if external else PAGES)
    allocator = assemble_stage(llvm, ALLOCATOR, run, BMO_DMA_LAB_PAGES=private_pages)
    mode = dict(BMO_EXTERNAL_SBEF=1) if external else {}
    if args.peer:
        mode['BMO_EXTERNAL_PEER'] = 1
    if win64:
        mode['BMO_EXTERNAL_WIN64'] = 1
    if args.msvc_process:
        mode['BMO_QEMU_WIN64_PROCESS'] = 1
    if args.msvc_minigzip_disk or args.msvc_minigzip_fat:
        mode['BMO_QEMU_GZIP_DISK'] = 1
    if args.msvc_minigzip_fat:
        mode['BMO_QEMU_GZIP_FAT'] = 1
    if args.msvc_dll_lifecycle:
        mode['BMO_EXTERNAL_DLL_LIFECYCLE'] = 1
    if args.msvc_tls:
        mode['BMO_EXTERNAL_TLS'] = 1
    if args.peer or win64:
        mode['BMO_EXTERNAL_EXT'] = 1
    if args.msvc_rebase:
        mode['BMO_EXTERNAL_REBASE'] = 1
    native_crt = None
    if args.msvc_crt_gs_native:
        native_crt = build_external_crt(ROOT, run, llvm / 'clang.exe', native_gs=True)
        delivery = native_crt[1]['cpu_exception']
        mode.update(BMO_GS_FAULT_PC=delivery['fault_pc'], BMO_GS_LANDING_PC=delivery['landing_pc'],
                    BMO_GS_PROLOGUE_FAULT_PC=delivery['prologue_fault_pc'],
                    BMO_GS_PROLOGUE_LANDING_PC=delivery['prologue_landing_pc'])
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
        run_external(args, run, llvm, bridge, body, stream, module, extension, native_crt=native_crt)
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
