"""Build the COFF client and its freestanding Win64 ABI fixture."""
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from ..importers.pe import pack_pe, pack_pe_with_dll, probe_pe
from ..diagnostics import Rejection
from ..importers.pe_bindings import SESSION_EXPORTS, WIN64_CONSOLE_PROFILE
from ..sbef.format import LEGACY_FORMAT_VERSION, inspect


def msvc_x64_compiler():
    vs = Path(os.environ['ProgramFiles']) / 'Microsoft Visual Studio'
    compilers = sorted(vs.glob('*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe'))
    cc = Path(shutil.which('cl.exe') or (compilers[-1] if compilers else 'cl.exe'))
    if not cc.is_file() or not cc.with_name('link.exe').is_file():
        raise ValueError('La prueba exige MSVC x64')
    return cc


def build_external_console(root, out, assembler):
    """Link the existing MSVC client against the external console import profile."""
    cc = msvc_x64_compiler()
    sdk = Path(os.environ['ProgramFiles(x86)']) / 'Windows Kits/10/Lib'
    libraries = sorted(sdk.glob('*/um/x64/kernel32.lib'))
    if not libraries:
        raise ValueError('La consola exige kernel32.lib del Windows SDK')
    abi = root / 'userspace/runtime/abi/win64'
    client, entry, pe = (out / name for name in ('console-client.obj', 'console-entry.obj', 'console.exe'))
    subprocess.run([cc, '/nologo', '/std:c++17', '/c', '/GS-', '/Zl', '/Od',
                    '/DBMO_MSVC_EXTERNAL_CONSOLE', f'/Fo{client}', root / 'tools/tests/msvc_sections.cpp'],
                   cwd=out, check=True)
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', abi / 'entry.S', '-o', entry], check=True)
    objects = [entry, client]
    for unit in ('portal', 'console_v1'):
        obj = out / f'console-{unit}.obj'
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc', '--crate-type=lib',
                        '--emit=obj', '-Cpanic=abort', '-Copt-level=2', abi / f'{unit}.rs', '-o', obj], check=True)
        objects.append(obj)
    link_map = out / 'console.map'
    profile = WIN64_CONSOLE_PROFILE
    exports = profile['Imports']
    subprocess.run([cc.with_name('link.exe'), '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152', '/fixed', '/Brepro',
                    '/incremental:no', '/merge:.pdata=.rdata', *('/include:' + name for name in exports.values()),
                    f'/map:{link_map}', f'/out:{pe}', *objects, libraries[-1]], cwd=out, check=True)
    pattern = r'^\s+[0-9A-Fa-f]+:[0-9A-Fa-f]+\s+(' + '|'.join(exports.values()) + r')\s+([0-9A-Fa-f]+)\b'
    symbols = {name: int(address, 16) for name, address in re.findall(pattern, link_map.read_text(), re.M)}
    if symbols.keys() != set(exports.values()):
        raise ValueError('Faltan simbolos de la consola MSVC')
    bindings = {api: symbols[name] for api, name in exports.items()}
    source = pe.read_bytes()
    payload = pack_pe(source, abi=profile['AbiVersion'], bindings=bindings)
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
    return payload, dict(profile=profile, imports=probe_pe(source)['Imports'],
                         pe_bytes=len(source), pe_sha256=hashlib.sha256(source).hexdigest(),
                         msvc_toolset=cc.parents[3].name, sdk=libraries[-1].parents[2].name,
                         rejected_import=rejected)


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
