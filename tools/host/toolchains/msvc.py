"""Build the COFF client and its freestanding Win64 ABI fixture."""
import gzip
import hashlib
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from ..importers.pe import pack_pe, pack_pe_gs_fixture, pack_pe_tls, pack_pe_with_dll, probe_pe
from ..diagnostics import Rejection
from ..importers.pe_bindings import (
    SESSION_EXPORTS, WIN64_CONSOLE_PROFILE, WIN64_FILE_PROFILE, WIN64_HEAP_PROFILE,
    WIN64_PROCESS_PROFILE, WIN64_SCRATCH_FILE_PROFILE,
)
from ..sbef.format import LEGACY_FORMAT_VERSION, inspect, load_plan


def msvc_x64_compiler():
    vs = Path(os.environ['ProgramFiles']) / 'Microsoft Visual Studio'
    compilers = sorted(vs.glob('*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe'))
    cc = Path(shutil.which('cl.exe') or (compilers[-1] if compilers else 'cl.exe'))
    if not cc.is_file() or not cc.with_name('link.exe').is_file():
        raise ValueError('La prueba exige MSVC x64')
    return cc


def build_external_tls(root, out, assembler):
    cc = msvc_x64_compiler()
    abi = root / 'userspace/runtime/abi/win64'
    client, directory, entry, portal, exe = (out / name for name in (
        'tls-client.obj', 'tls-directory.obj', 'tls-entry.obj', 'tls-portal.obj', 'tls-client.exe'))
    subprocess.run([cc, '/nologo', '/std:c++20', '/c', '/GS-', '/Zl', '/O2', '/Zc:tlsGuards-', f'/Fo{client}',
                    root / 'tools/tests/msvc_tls_client.cpp'], cwd=out, check=True)
    for source, obj in ((abi / 'entry.S', entry), (root / 'tools/tests/msvc_tls_directory.S', directory)):
        subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', source, '-o', obj], check=True)
    subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc', '--crate-type=lib',
                    '--emit=obj', '-Cpanic=abort', '-Copt-level=2', abi / 'portal.rs', '-o', portal], check=True)
    subprocess.run([cc.with_name('link.exe'), '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/fixed', '/Brepro', '/incremental:no', '/entry:bmo_win64_start', '/base:0x3fe00000',
                    '/align:2097152', '/merge:.pdata=.rdata', '/include:_tls_used',
                    f'/out:{exe}', entry, client, directory, portal], cwd=out, check=True)
    package = out / 'tls-client.sbef'
    report = json.loads(subprocess.check_output([sys.executable, '-B', root / 'tools/sbef.py', 'pack', exe,
                        package, '--abi', '1', '--producer', 'msvc', '--static-tls']))
    if (report['StaticTLS']['TemplateBytes'], report['StaticTLS']['ZeroFillBytes']) != (16, 8):
        raise ValueError('El perfil de prueba espera 16 bytes de plantilla y 8 de relleno')
    source = bytearray(exe.read_bytes())
    info = probe_pe(source)
    rva = info['Directories']['tls']['RVA']
    section = next(item for item in info['Sections'] if item['RVA'] <= rva < item['RVA'] + item['FileBytes'])
    offset = section['FileOffset'] + rva - section['RVA']
    struct.pack_into('<Q', source, offset + 24, info['ImageBase'] + rva)
    try:
        pack_pe_tls(source, abi=1)
    except Rejection as error:
        if error.code != 'PE-TLS-CALLBACK':
            raise
        report['RejectedCallback'] = error.report()
    else:
        raise ValueError('HOST admitio un callback TLS fuera del perfil')
    report['MsvcToolset'] = cc.parents[3].name
    return package.read_bytes(), report


def build_external_console(root, out, assembler, *, heap=False, package_file=False,
                           use_clang=False, gzip_source=None, minigzip_args=None, corrupt_input=False,
                           minigzip_input=None, minigzip_disk=False, minigzip_fat=False, process_exit=None):
    """Link the existing MSVC client against the external console import profile."""
    cc = msvc_x64_compiler()
    sdk = Path(os.environ['ProgramFiles(x86)']) / 'Windows Kits/10/Lib'
    libraries = sorted(sdk.glob('*/um/x64/kernel32.lib'))
    if not libraries:
        raise ValueError('La consola exige kernel32.lib del Windows SDK')
    abi = root / 'userspace/runtime/abi/win64'
    client, entry, pe = (out / name for name in ('console-client.obj', 'console-entry.obj', 'console.exe'))
    compiler = assembler.with_name('clang-cl.exe') if use_clang else cc
    package_file = package_file or gzip_source is not None
    defines = ['/DBMO_MSVC_EXTERNAL_HEAP'] if heap or package_file else []
    units = ['portal', 'console_v1']
    profile = WIN64_CONSOLE_PROFILE
    file_report = {}
    if heap or package_file:
        units.append('process_heap')
        profile = WIN64_HEAP_PROFILE
    env = None
    argv_data = None
    command_strings = {}
    if package_file:
        seed = 19 if use_clang else 7
        contents = bytes((29 * index + seed) & 255 for index in range(1027))
        if minigzip_input is not None:
            contents = minigzip_input
        elif gzip_source is not None:
            original = bytes((index // 13 * 29 + index % 11 * seed) & 255 for index in range(2048))
            (out / 'expected-output.bin').write_bytes(original)
            contents = (original if minigzip_args is not None and '-d' not in minigzip_args
                        else gzip.compress(original, mtime=0))
            if corrupt_input:
                contents = contents[:-8] + bytes([contents[-8] ^ 1]) + contents[-7:]
        source_file = out / 'input.bin'
        source_file.write_bytes(contents)
        env = {**os.environ, 'BMO_PACKAGE_INPUT': str(source_file.resolve())}
        if minigzip_args is not None:
            argv_path = out / 'argv.bin'
            argv_data = b'\0'.join(arg.encode('ascii') for arg in ('minigzip', *minigzip_args)) + b'\0'
            argv_path.write_bytes(argv_data)
            env['BMO_PACKAGE_ARGV'] = str(argv_path.resolve())
        units.extend(('package_file', 'last_error'))
        defines.extend(['/DBMO_MSVC_PACKAGE_FILE', f'/DBMO_PACKAGE_SEED={seed}'])
        profile = WIN64_FILE_PROFILE
        if gzip_source is not None:
            profile = WIN64_SCRATCH_FILE_PROFILE
        file_report = dict(package_file=dict(path=source_file.name, bytes=len(contents),
                                             sha256=hashlib.sha256(contents).hexdigest()))
    compile_flags = ['/Od', '/DBMO_MSVC_EXTERNAL_CONSOLE', *defines]
    client_source = root / 'tools/tests/msvc_sections.cpp'
    objects = [entry, client]
    if process_exit is not None:
        argv = ['minigzip demo.exe', '-c', '', 'datos \u00f1\U0001f600.bin', 'a"b', 'C:\\dir con espacio\\']
        command = subprocess.list2cmdline(argv)
        env = dict(os.environ)
        for suffix, encoding in (('', 'utf-16-le'), ('_A', 'utf-8')):
            command_bytes = (command + '\0').encode(encoding)
            command_path = out / f'command-line-{encoding}.bin'
            command_path.write_bytes(command_bytes)
            env[f'BMO_WIN64_CMDLINE{suffix}'] = str(command_path.resolve())
            command_strings[f'BMO_WIN64_COMMAND_LINE{suffix}'] = (command_bytes, 1 if suffix else 2)
        units.extend(('process_start', 'last_error'))
        profile = WIN64_PROCESS_PROFILE
        compile_flags = ['/O1', f'/DBMO_WIN64_EXIT_CODE=0x{process_exit:08x}UL']
        client_source = root / 'tools/tests/msvc_process_start.cpp'
        file_report.update(argv=argv, command_line=command, ansi_code_page=65001, exit_code=process_exit)
    if gzip_source is not None:
        gzip_source = gzip_source.resolve(strict=True)
        compile_flags = ['/O1', '/DZ_SOLO', f'/I{gzip_source}']
        if minigzip_args is not None:
            compile_flags.append('/DBMO_MINIGZIP_CLI')
        if minigzip_disk:
            compile_flags.append('/DBMO_MINIGZIP_DISK')
        if minigzip_fat:
            compile_flags.append('/DBMO_MINIGZIP_FAT')
        client_source = root / 'tools/tests/msvc_gzip.cpp'
        for name in ('infback', 'inffast', 'inftrees', 'deflate', 'trees', 'adler32', 'crc32', 'zutil'):
            obj = out / f'{name}.obj'
            flags = ['/clang:-ffreestanding'] if use_clang else ['/Oi-']
            subprocess.run([compiler, '/nologo', '/c', '/GS-', '/Zl', '/Gy', *flags,
                            *compile_flags, f'/Fo{obj}', gzip_source / f'{name}.c'],
                           cwd=out, check=True)
            objects.append(obj)
        header = (gzip_source / 'zlib.h').read_bytes()
        file_report['zlib_header_sha256'] = hashlib.sha256(header).hexdigest()
    subprocess.run([compiler, '/nologo', '/std:c++17', '/c', '/GS-', '/Zl',
                    *compile_flags, f'/Fo{client}', client_source],
                   cwd=out, check=True)
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', abi / 'entry.S', '-o', entry], check=True)
    for unit in units:
        obj = out / f'console-{unit}.obj'
        scratch = gzip_source is not None and unit == 'package_file'
        rust_flags = ['--cfg', 'bmo_package_output'] if scratch else []
        if scratch and minigzip_args is not None:
            rust_flags += ['--cfg', 'bmo_package_argv']
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc', '--crate-type=lib',
                        '--emit=obj', '-Cpanic=abort', '-Copt-level=s' if scratch else '-Copt-level=2',
                        *rust_flags, abi / f'{unit}.rs', '-o', obj],
                       check=True, env=env if unit in ('package_file', 'process_start') else None)
        objects.append(obj)
    link_map = out / 'console.map'
    exports = profile['Imports']
    if gzip_source is not None:
        unused = {'GetTickCount64', 'HeapReAlloc', 'HeapSize', 'GetFileType', 'GetFileSizeEx'}
        if minigzip_args is not None:
            unused.update(('GetLastError', 'SetFilePointerEx', 'SetEndOfFile', 'FlushFileBuffers'))
        exports = {api: target for api, target in exports.items() if api not in unused}
    subprocess.run([cc.with_name('link.exe'), '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152', '/fixed', '/Brepro',
                    '/incremental:no', '/merge:.pdata=.rdata', *('/include:' + name for name in exports.values()),
                    f'/map:{link_map}', f'/out:{pe}', *objects, libraries[-1]], cwd=out, check=True)
    names = set(exports.values()) | command_strings.keys()
    pattern = r'^\s+[0-9A-Fa-f]+:[0-9A-Fa-f]+\s+(' + '|'.join(sorted(names)) + r')\s+([0-9A-Fa-f]+)\b'
    symbols = {name: int(address, 16) for name, address in re.findall(pattern, link_map.read_text(), re.M)}
    if symbols.keys() != names:
        raise ValueError('Faltan simbolos de la consola MSVC')
    bindings = {api: symbols[name] for api, name in exports.items()}
    source = pe.read_bytes()
    payload = pack_pe(source, abi=profile['AbiVersion'], bindings=bindings)
    if package_file or command_strings:
        readonly = next(region for region in load_plan(payload)['Regions'] if region['Permissions'] == 'R')
        start = readonly['FileOffset']
        readonly_bytes = payload[start:start + readonly['FileBytes']]
        if package_file and contents not in readonly_bytes:
            raise ValueError('El archivo de entrada debe quedar en una region de solo lectura')
        if argv_data is not None:
            if argv_data not in readonly_bytes:
                raise ValueError('Los argumentos deben quedar en una region de solo lectura')
            file_report.update(argv=['minigzip', *minigzip_args],
                               argv_sha256=hashlib.sha256(argv_data).hexdigest())
        for symbol, (command_bytes, alignment) in command_strings.items():
            address = symbols[symbol]
            offset = address - readonly['VirtualStart']
            if address % alignment or offset < 0 or readonly_bytes[offset:offset + len(command_bytes)] != command_bytes:
                raise ValueError(f'{symbol} debe quedar alineado en una region de solo lectura')
            key = 'command_line_a' if symbol.endswith('_A') else 'command_line'
            file_report[f'{key}_va'] = address
            file_report[f'{key}_sha256'] = hashlib.sha256(command_bytes).hexdigest()
    (out / 'console.sbef').write_bytes(payload)

    # Change only the imported name and exercise the same binder before QEMU.
    unknown = source.replace(b'WriteFile\x00', b'OtherFile\x00', 1)
    try:
        pack_pe(unknown, abi=profile['AbiVersion'], bindings=bindings)
    except Rejection as error:
        rejected = error.report()
        if rejected['Code'] != 'PE-SESSION-IMPORT' or rejected['Field'] != 'KERNEL32.dll!OtherFile':
            raise
    else:
        raise ValueError('HOST admitio una importacion fuera del catalogo')
    return payload, dict(profile={**profile, 'Imports': exports}, imports=probe_pe(source)['Imports'],
                         pe_bytes=len(source), pe_sha256=hashlib.sha256(source).hexdigest(),
                         producer='clang-cl' if use_clang else 'msvc',
                         msvc_toolset=cc.parents[3].name, sdk=libraries[-1].parents[2].name,
                         rejected_import=rejected, **file_report)


def build_external_crt(root, out, assembler, *, guarded=False, native_gs=False):
    """Link the BMO-X2 startup with selected functions from the real static UCRT."""
    guarded = guarded or native_gs
    cc = msvc_x64_compiler()
    sdk = Path(os.environ['ProgramFiles(x86)']) / 'Windows Kits/10/Lib'
    libraries = sorted(sdk.glob('*/ucrt/x64/libucrt.lib'))
    if not libraries:
        raise ValueError('La prueba CRT exige libucrt.lib x64 del Windows SDK')
    ucrt = libraries[-1]
    abi = root / 'userspace/runtime/abi/win64'
    client, startup, entry, exe, link_map = (out / name for name in (
        'crt-client.obj', 'crt-startup.obj', 'crt-entry.obj', 'crt.exe', 'crt.map'))
    for source, obj in ((root / 'tools/tests/msvc_crt_client.cpp', client),
                        (abi / 'crt_startup.cpp', startup)):
        gs = ['/GS', '/DBMO_CRT_GS'] if guarded and obj == client else ['/GS-']
        if native_gs and obj == client:
            gs.append('/DBMO_CRT_GS_NATIVE')
        subprocess.run([cc, '/nologo', '/c', '/MT', *gs, '/Zl', '/Od', f'/Fo{obj}', source],
                       cwd=out, check=True)
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', abi / 'entry.S', '-o', entry],
                   check=True)
    objects = [entry, startup, client]
    if guarded:
        objdump = assembler.with_name('llvm-objdump.exe')
        relocations = subprocess.check_output([objdump, '-r', client], text=True)
        msvc_handler_required = '__GSHandlerCheck' in relocations
        client_compiler = 'MSVC'
        if msvc_handler_required and not native_gs:
            # The fixed PE loader rejects exception handlers. Exercise the
            # Win64 cookie ABI with a compiler that emits the epilogue alone.
            protected = assembler.with_name('clang-cl.exe')
            subprocess.run([protected, '/nologo', '/c', '/MT', '/GS', '/DBMO_CRT_GS',
                            '/Zl', '/Od', f'/Fo{client}', root / 'tools/tests/msvc_crt_client.cpp'],
                           cwd=out, check=True)
            relocations = subprocess.check_output([objdump, '-r', client], text=True)
            client_compiler = 'clang-cl'
        if not re.search(r'IMAGE_REL_AMD64_REL32\s+__security_check_cookie\s*$', relocations, re.MULTILINE):
            raise ValueError('El compilador no emitio la llamada de comprobacion /GS')
        gs_obj = out / 'crt-gs.obj'
        seed = secrets.randbits(47) | (1 << 47)
        native_define = ['-DBMO_GS_NATIVE'] if native_gs else []
        subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', *native_define,
                        f'-DBMO_GS_COOKIE={seed}', root / 'tools/tests/msvc_crt_gs.S', '-o', gs_obj],
                       check=True)
        objects.append(gs_obj)
    for unit in ('portal', 'console_v1'):
        obj = out / f'crt-{unit}.obj'
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc', '--crate-type=lib',
                        '--emit=obj', '-Cpanic=abort', '-Copt-level=2', abi / f'{unit}.rs', '-o', obj], check=True)
        objects.append(obj)
    libcmt = cc.parents[3] / 'lib/x64/libcmt.lib'
    runtime = [ucrt]
    if native_gs:
        dispatch = out / 'gs-dispatch.obj'
        sdk_headers = sdk.parent / 'Include' / ucrt.parents[2].name
        include_flags = [f'/I{cc.parents[3] / "include"}',
                         *(f'/I{sdk_headers / part}' for part in ('um', 'shared', 'ucrt'))]
        # Keep this guest within the external FAT32 probe's existing size cap.
        subprocess.run([cc, '/nologo', '/c', '/GS-', '/Zl', '/O1', f'/Fo{dispatch}',
                        *include_flags, root / 'tools/tests/msvc_crt_gs_dispatch.cpp'], cwd=out, check=True)
        objects.append(dispatch)
        archiver = assembler.with_name('llvm-ar.exe')
        members = subprocess.check_output([archiver, 't', libcmt], text=True).splitlines()
        for name in ('gshandler.obj', 'amdsecgs.obj'):
            matches = [member for member in members if Path(member).name.lower() == name]
            if len(matches) != 1:
                raise ValueError(f'libcmt.lib debe contener un miembro {name}')
            target = out / name
            target.write_bytes(subprocess.check_output([archiver, 'p', libcmt, matches[0]]))
            runtime.append(target)
    subprocess.run([cc.with_name('link.exe'), '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152', '/fixed', '/Brepro',
                    '/incremental:no', '/merge:.pdata=.rdata', '/merge:.CRT=.rdata',
                    f'/map:{link_map}', f'/out:{exe}', *objects, *runtime],
                   cwd=out, check=True)
    expected = {'abs', 'llabs', 'strlen', 'strcmp', 'strncmp'}
    if native_gs:
        expected.update(('strspn', 'strcspn'))
    map_text = link_map.read_text()
    vendor_symbols = dict(re.findall(
        r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+(\w+)\s+[0-9a-fA-F]+[^\S\r\n]+(?:f +)?'
        r'(libucrt:[^\s]+)\s*$', map_text, re.MULTILINE))
    if expected - vendor_symbols.keys():
        raise ValueError(f'Faltan funciones de libucrt.lib en el MAP: {sorted(expected - vendor_symbols.keys())}')
    source = exe.read_bytes()
    native_report = {}
    if native_gs:
        gs_symbols = {
            name: (int(address, 16), origin)
            for name, address, origin in re.findall(
                r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+(__GSHandlerCheck|__security_check_cookie)'
                r'\s+([0-9a-fA-F]+)\s+f\s+(gshandler\.obj|amdsecgs\.obj)\s*$', map_text, re.MULTILINE)
        }
        if {name: member for name, (_, member) in gs_symbols.items()} != {
            '__GSHandlerCheck': 'gshandler.obj',
            '__security_check_cookie': 'amdsecgs.obj',
        }:
            raise ValueError('El MAP debe atribuir los dos helpers /GS a libcmt.lib')
        info = probe_pe(source)
        handler = gs_symbols['__GSHandlerCheck'][0] - info['ImageBase']
        seh_symbol = re.search(
            r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+__C_specific_handler\s+([0-9a-fA-F]+)\s+f\s+gs-dispatch\.obj',
            map_text, re.MULTILINE)
        if seh_symbol is None:
            raise ValueError('Falta __C_specific_handler del banco en el MAP')
        seh_handler = int(seh_symbol[1], 16) - info['ImageBase']
        dispatch_symbol = re.search(
            r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+bmo_gs_image\s+([0-9a-fA-F]+)\s+',
            map_text, re.MULTILINE)
        if dispatch_symbol is None:
            raise ValueError('Falta el descriptor del banco GS en el MAP')
        fault_symbols = {name: int(address, 16) for name, address in re.findall(
            r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+bmo_test_gs_(cpu_ud|cpu_landing|prologue_fault|prologue_landing)'
            r'\s+([0-9a-fA-F]+)\s+',
            map_text, re.MULTILINE)}
        code = next(section for section in info['Sections'] if section['Executable'])
        code_start = info['ImageBase'] + code['RVA']
        code_end = code_start + min(code['VirtualBytes'], code['FileBytes'])
        if (fault_symbols.keys() != {'cpu_ud', 'cpu_landing', 'prologue_fault', 'prologue_landing'} or
                not all(code_start <= addr < code_end for addr in fault_symbols.values()) or
                len(set(fault_symbols.values())) != 4):
            raise ValueError('El origen y destino #UD deben estar enlazados en .text')
        for name in ('cpu_ud', 'prologue_fault'):
            fault_offset = code['FileOffset'] + fault_symbols[name] - code_start
            if fault_symbols[name] + 4 > code_end or source[fault_offset:fault_offset + 4] != b'\x0f\x0b' * 2:
                raise ValueError(f'Cambio la instruccion #UD del banco {name}')
        descriptor = int(dispatch_symbol[1], 16) - info['ImageBase']
        readonly = next(section for section in info['Sections'] if section['Name'] == '.rdata')
        start = readonly['RVA']
        end = start + min(readonly['VirtualBytes'], readonly['FileBytes'])
        directory = info['Directories']['exceptions']
        if not start <= descriptor <= end - 24 or descriptor % 8:
            raise ValueError('El descriptor GS debe estar alineado en .rdata')
        offset = readonly['FileOffset'] + descriptor - start
        image = bytearray(source)
        if struct.unpack_from('<Q4I', image, offset) != (0x424d4f4753444953, 0, 0, 0, 0):
            raise ValueError('Cambio el descriptor GS de entrada')
        struct.pack_into('<Q4I', image, offset, info['ImageBase'],
                         directory['RVA'], directory['Bytes'], start, end)
        source = bytes(image)
        for action, code in ((lambda: pack_pe(source, abi=1), 'PE-UNWIND-INFO'),
                             (lambda: pack_pe_gs_fixture(source, handler + 1, seh_handler_rva=seh_handler),
                              'PE-UNWIND-GS-HANDLER')):
            try:
                action()
            except Rejection as error:
                if error.code != code:
                    raise
            else:
                raise ValueError(f'HOST debia rechazar la prueba {code}')
        payload = pack_pe_gs_fixture(source, handler, seh_handler_rva=seh_handler)
        exe.write_bytes(source)
        frame_symbols = {name: int(address, 16) - info['ImageBase'] for name, address in re.findall(
            r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+bmo_test_gs_(call_client|chained_fragment)'
            r'\s+([0-9a-fA-F]+)\s+', map_text, re.MULTILINE)}
        if frame_symbols.keys() != {'call_client', 'chained_fragment'}:
            raise ValueError('Faltan los marcos unwind del fixture en el MAP')
        table = readonly['FileOffset'] + directory['RVA'] - start
        records = {begin: unwind for begin, _, unwind in struct.iter_unpack(
            '<III', source[table:table + directory['Bytes']])}
        if not all(rva in records for rva in frame_symbols.values()):
            raise ValueError('Los marcos de prueba deben tener entrada en .pdata')
        native_report = dict(
            libcmt_sha256=hashlib.sha256(libcmt.read_bytes()).hexdigest(),
            gs_symbols={name: origin for name, (_, origin) in sorted(gs_symbols.items())},
            unwind_inventory=info['UnwindInventory'],
            fault_policy='QEMU one-shot delivery for either registered #UD PC; abort otherwise',
            dispatch_fixture=dict(exception_table_rva=directory['RVA'], exception_table_bytes=directory['Bytes'],
                                  handler_rva=handler, seh_handler_rva=seh_handler,
                                  trigger='synchronous call with live MSVC frame'),
            cpu_exception=dict(vector=6, fault_pc=fault_symbols['cpu_ud'], landing_pc=fault_symbols['cpu_landing'],
                               prologue_fault_pc=fault_symbols['prologue_fault'],
                               prologue_landing_pc=fault_symbols['prologue_landing'],
                               image_base=info['ImageBase'],
                               unwind_rvas={name: records[rva] for name, rva in frame_symbols.items()}),
            default_rejection='PE-UNWIND-INFO', wrong_handler_rejection='PE-UNWIND-GS-HANDLER',
        )
    else:
        payload = pack_pe(source, abi=1)
    (out / 'crt.sbef').write_bytes(payload)
    report = dict(
        startup='bmo_crt_initialize / bmo_crt_client_main / bmo_crt_finalize',
        build=(f'{client_compiler} /MT /GS /Zl; MSVC startup object; BMO-X2 entry; explicit static libucrt.lib'
               if guarded else 'MSVC /MT /GS- /Zl; BMO-X2 entry; explicit static libucrt.lib'),
        functions={name: vendor_symbols[name] for name in sorted(expected)},
        pe_bytes=len(source), pe_sha256=hashlib.sha256(source).hexdigest(),
        msvc_toolset=cc.parents[3].name, sdk=ucrt.parents[2].name,
        libucrt_sha256=hashlib.sha256(ucrt.read_bytes()).hexdigest(),
        **native_report,
    )
    if guarded:
        match = re.search(r'^\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+bmo_gs_test_mode\s+([0-9a-fA-F]+)\s+',
                          map_text, re.MULTILINE)
        if match is None:
            raise ValueError('El modo de prueba /GS no esta en el MAP')
        report['stack_cookie'] = dict(test_mode_address=int(match[1], 16),
                                      seed='48-bit build-time HOST test seed',
                                      msvc_handler_required=msvc_handler_required,
                                      fail_fast='CPL3 UD2 with marker 4753434B')
    return payload, report


def build_external_dll(root, out, assembler, *, lifecycle=False, reject_attach=False):
    """Build independently linked EXE and DLL inputs, then use the public HOST CLI."""
    cc = msvc_x64_compiler()
    linker = cc.with_name('link.exe')
    module_obj, client_obj, dll, exe = (out / name for name in (
        'module.obj', 'dll-client.obj', 'module.dll', 'dll-client.exe'))
    defines = ['/DBMO_DLL_LIFECYCLE'] if lifecycle else []
    for unit, obj in (('msvc_dll_module.cpp', module_obj), ('msvc_dll_client.cpp', client_obj)):
        reject = ['/DBMO_DLL_REJECT_ATTACH'] if unit == 'msvc_dll_module.cpp' and reject_attach else []
        optimize = '/Od' if lifecycle and obj == client_obj else '/O2'
        subprocess.run([cc, '/nologo', '/c', '/GS-', '/Zl', optimize, *defines, *reject, f'/Fo{obj}',
                        root / 'tools/tests' / unit], cwd=out, check=True)
    import_lib = out / 'module.lib'
    common_link = ['/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                   '/fixed', '/Brepro', '/incremental:no']
    dll_entry = ['/entry:DllMain', '/export:BmoDllEntry=DllMain'] if lifecycle else ['/noentry']
    subprocess.run([linker, *common_link, '/dll', *dll_entry, '/base:0x40800000',
                    f'/out:{dll}', f'/implib:{import_lib}', module_obj], cwd=out, check=True)
    abi = root / 'userspace/runtime/abi/win64'
    entry, portal = out / 'dll-entry.obj', out / 'dll-portal.obj'
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', abi / 'entry.S', '-o', entry], check=True)
    subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc', '--crate-type=lib',
                    '--emit=obj', '-Cpanic=abort', '-Copt-level=2', abi / 'portal.rs', '-o', portal], check=True)
    startup = []
    if lifecycle:
        for unit in ('dll_lifecycle', 'crt_startup'):
            runtime = out / f'{unit}.obj'
            subprocess.run([cc, '/nologo', '/c', '/GS-', '/Zl', '/Od', f'/Fo{runtime}',
                            abi / f'{unit}.cpp'], cwd=out, check=True)
            startup.append(runtime)
    startup_sections = ['/merge:.CRT=.rdata'] if lifecycle else []
    subprocess.run([linker, *common_link, '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152',
                    '/merge:.pdata=.rdata', *startup_sections, f'/out:{exe}', entry, client_obj, portal,
                    *startup, import_lib],
                   cwd=out, check=True)

    package = out / 'dll-client.sbef'
    dll_option = '--with-dll-lifecycle' if lifecycle else '--with-dll'
    report = json.loads(subprocess.check_output([sys.executable, '-B', root / 'tools/sbef.py', 'pack', exe,
                        package, '--abi', '1', '--producer', 'msvc', dll_option, dll]))
    dll_bytes = dll.read_bytes()
    if lifecycle:
        bad_entry = bytearray(dll_bytes)
        pe_offset, = struct.unpack_from('<I', bad_entry, 0x3c)
        module = report['LinkedModule']
        step_rva = int(module['Exports']['BmoStep'], 16) - int(module['ImageBase'], 16)
        struct.pack_into('<I', bad_entry, pe_offset + 40, step_rva)
        try:
            pack_pe_with_dll(exe.read_bytes(), bad_entry, abi=1, lifecycle=True)
        except Rejection as error:
            if error.code != 'PE-DLL-ENTRY':
                raise
            report['RejectedEntry'] = error.report()
        else:
            raise ValueError('HOST admitio una DLL con una entrada que no coincide con BmoDllEntry')
    unknown_export = dll_bytes.replace(b'BmoStep\x00', b'BadStep\x00', 1)
    try:
        pack_pe_with_dll(exe.read_bytes(), unknown_export, abi=1, lifecycle=lifecycle)
    except Rejection as error:
        if error.code != 'PE-SESSION-IMPORT' or error.field.lower() != 'module.dll!bmostep':
            raise
        report['RejectedExport'] = error.report()
    else:
        raise ValueError('HOST admitio una DLL que no exporta BmoStep')
    report['MsvcToolset'] = cc.parents[3].name
    return package.read_bytes(), report


def build_desktop_panel(root, out, cc, nm):
    """Extract a trusted in-process MSVC function, with no COFF fixups."""
    obj = out/'msvc-panel.obj'
    subprocess.run([cc, '/nologo', '/std:c++17', '/c', '/Od', '/GS-', '/Zl',
                    f'/Fo{obj}', str(root/'tools/tests/msvc_desktop_panel.cpp')],
                   check=True, cwd=out)
    data = obj.read_bytes()
    header = struct.Struct('<HHIIIHH')
    section = struct.Struct('<8sIIIIIIHHI')
    if len(data) < header.size:
        raise ValueError('MSVC panel COFF header')
    machine, count, _, _, _, optional, _ = header.unpack_from(data)
    if machine != 0x8664 or optional or header.size + count * section.size > len(data):
        raise ValueError('MSVC panel COFF header')
    executable = []
    for i in range(count):
        name, _, _, size, offset, _, _, relocations, _, flags = section.unpack_from(
            data, header.size + i * section.size)
        if flags & 0x20000000:
            if (name.rstrip(b'\0') not in (b'.text', b'.text$mn') or relocations
                    or flags & 0x80000000 or not 0 < size <= 4096
                    or not header.size + count * section.size <= offset <= len(data) - size):
                raise ValueError('MSVC panel requires one relocation-free .text')
            executable.append(data[offset:offset+size])
    names = subprocess.check_output([str(nm), '--format=posix', str(obj)], text=True)
    symbols = [line.split() for line in names.splitlines() if len(line.split()) >= 2]
    entries = [row for row in symbols if row[0] == 'bmo_msvc_panel' and row[1] == 'T']
    if len(executable) != 1 or len(entries) != 1 or int(entries[0][2], 16) != 0 or any(row[1]=='U' for row in symbols):
        raise ValueError('MSVC panel symbol or dependencies')
    binary = out/'msvc-panel.bin'
    binary.write_bytes(executable[0])
    return binary


def build_win64_client(out, client, abi, completion, *, producer, cc, linker, assembler, qemu):
    obj = out / ('client-qemu.obj' if qemu else 'client.obj')
    flags = ['/DBMO_ABI_QEMU'] if qemu else []
    target = ['--target=x86_64-pc-windows-msvc'] if producer == 'clang-cl' else []
    subprocess.run([cc, *target, '/nologo', '/std:c11', '/c', '/O2', '/GS-', '/Zl', *flags,
                    f'/Fo{obj}', str(client)], check=True, cwd=out)
    data = obj.read_bytes()
    if data[:2] != b'\x64\x86' or not all(name in data for name in (b'bmo_invoke', b'bmo_wait')):
        raise ValueError('ABI-TOOLCHAIN: objeto COFF o simbolos de llamada invalidos')
    report = dict(Toolchain=producer, Stage='COFF', Bytes=len(data),
                  SHA256=hashlib.sha256(data).hexdigest())
    if not linker:
        return report, None

    portal = out / 'portal-win64.obj'
    subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc',
                    '--crate-type=lib', '--emit=obj', '-Cpanic=abort', '-Copt-level=2',
                    str(abi/'win64/portal.rs'), '-o', str(portal)], check=True, cwd=out)
    pe = out / ('client-qemu.exe' if qemu else 'client.exe')
    objects = [obj, portal]
    link_flags = ['/entry:bmo_main']
    if qemu:
        for source in (abi/'win64/entry.S', completion):
            unit = out / (source.stem+'-win64.obj')
            subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c',
                            str(source), '-o', str(unit)], check=True, cwd=out)
            objects.append(unit)
        # Place the one RX section at the CASM fixture's fixed address.
        link_flags = ['/entry:bmo_win64_start', '/base:0x3fff0000', '/align:65536', '/fixed', '/Brepro',
                      '/merge:.rdata=.text', '/merge:.pdata=.text']
    subprocess.run([linker, '/nologo', '/machine:x64', '/nodefaultlib',
                    '/subsystem:console', '/incremental:no', *link_flags,
                    f'/out:{pe}', *map(str, objects)], check=True, cwd=out)
    pe_bytes = pe.read_bytes()
    image = probe_pe(pe_bytes)
    if any(name in image['Directories'] for name in ('imports', 'delay_imports', 'tls')):
        raise ValueError('ABI-TOOLCHAIN: PE freestanding con dependencias inesperadas')
    report.update(Stage='PE32+ inspection', Image=image, PESHA256=hashlib.sha256(pe_bytes).hexdigest(),
                  RustPortalBytes=portal.stat().st_size)
    if not qemu:
        return report, None

    sbef = out / 'client-qemu.sbef'
    # The frozen embedded ABI fixture still consumes the v1 wire format.
    payload = pack_pe(pe_bytes, abi=1, format_version=LEGACY_FORMAT_VERSION)
    sbef.write_bytes(payload)
    report.update(Stage='SBEF', SBEF=inspect(payload), SBEFSHA256=hashlib.sha256(payload).hexdigest())
    return report, sbef


def verify_msvc_sections(root, out, reference, *, cc, linker, assembler, objcopy, sdk_lib, window):
    out.mkdir(parents=True, exist_ok=True)
    abi = root/'userspace/runtime/abi/win64'
    obj, pe, sbef = (out/name for name in ('client.obj', 'client.exe', 'client.sbef'))
    # The visual fixture uses the existing no-chain unwind admission profile.
    flags = ['/Od', '/DBMO_MSVC_WINDOW'] if window else ['/O2']
    subprocess.run([cc, '/nologo', '/std:c++17', '/c', '/GS-', '/Zl', *flags, f'/Fo{obj}',
                    str(root/'tools/tests/msvc_sections.cpp')], check=True, cwd=out)
    entry = out/'entry.obj'
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', str(abi/'entry.S'),
                    '-o', str(entry)], check=True)
    objects = [entry, obj]
    units = ('portal', 'session_clock', 'session_console')
    if window:
        units += ('session_present',)
        model = out/'libbmo_director.rlib'
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc',
                        '--crate-type=rlib', '--crate-name=bmo_director', '-Cpanic=abort', '-Copt-level=2',
                        str(root/'userspace/services/desktop/src/lib.rs'), '-o', str(model)], check=True)
    for unit in units:
        director = unit == 'session_present'
        target = out/(unit+('.lib' if director else '.obj'))
        dependencies = ['--extern', f'bmo_director={model}', '-Clto=fat', '-Ccodegen-units=1'] if director else []
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc',
                        ('--crate-type=staticlib' if director else '--crate-type=lib'),
                        ('--emit=link' if director else '--emit=obj'),
                        '-Cpanic=abort', '-Copt-level=2', *dependencies,
                        str(abi/(unit+'.rs')), '-o', str(target)], check=True)
        objects.append(target)
    link_map = out/'client.map'
    subprocess.run([linker, '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152',
                    '/fixed', '/Brepro', '/incremental:no', '/merge:.pdata=.rdata',
                    *('/include:'+name for name in SESSION_EXPORTS.values()),
                    f'/map:{link_map}', f'/out:{pe}', *map(str, objects), sdk_lib], check=True)
    names = ('phase', 'first_ms', 'second_ms', 'scratch', 'written', *SESSION_EXPORTS.values())
    if window:
        names += ('director_pixels', 'director_state')
    pattern = r'^\s+[0-9A-Fa-f]+:[0-9A-Fa-f]+\s+(' + '|'.join(names) + r')\s+([0-9A-Fa-f]+)\b'
    symbols = {name: int(address, 16) for name, address in re.findall(pattern, link_map.read_text(), re.M)}
    if set(symbols) != set(names):
        raise ValueError('Missing MSVC fixture symbols')
    pe_bytes = pe.read_bytes()
    bindings = {api: symbols.pop(name) for api, name in SESSION_EXPORTS.items()}
    payload = pack_pe(pe_bytes, abi=1, bindings=bindings)
    sbef.write_bytes(payload)
    manifest = out/'symbols.json'
    manifest.write_text(json.dumps(symbols), encoding='ascii')
    for name, source in (('gate', 'kernel/syscalls/session_gate.S'),
                         ('loader', 'kernel/loader/doom_engine_loader.S')):
        subprocess.run([assembler, '--target=x86_64-unknown-none-elf', '-DDOOM_ENGINE', '-DDESKTOP_DOOM',
                        '-c', str(root/source), '-o', str(out/(name+'.o'))], check=True)
        subprocess.run([objcopy, '-O', 'binary', '--only-section=.text',
                        str(out/(name+'.o')), str(out/(name+'.bin'))], check=True)
    print(json.dumps(dict(Toolchain='msvc', Imports=probe_pe(pe_bytes)['Imports'],
                          Image=inspect(payload)), indent=2), flush=True)
    subprocess.run([sys.executable, '-B', str(root/'tools/boot/doom_qemu.py'),
                    str(reference.resolve()), str(sbef), '--msvc-sections', str(manifest),
                    '--session-gate', str(out/'gate.bin'), '--external-loader', str(out/'loader.bin')],
                   check=True)
