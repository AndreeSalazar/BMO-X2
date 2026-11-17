"""Build the COFF client and its freestanding Win64 ABI fixture."""
import hashlib
import json
import re
import subprocess
import sys

from ..importers.pe import pack_pe, probe_pe
from ..importers.pe_bindings import SESSION_EXPORTS
from ..sbef.format import inspect


def build_msvc(out, client, abi, completion, *, cc, linker, assembler, qemu):
    obj = out / ('client-qemu.obj' if qemu else 'client.obj')
    flags = ['/DBMO_ABI_QEMU'] if qemu else []
    subprocess.run([cc, '/nologo', '/std:c11', '/c', '/O2', '/GS-', '/Zl', *flags,
                    f'/Fo{obj}', str(client)], check=True, cwd=out)
    data = obj.read_bytes()
    if data[:2] != b'\x64\x86' or not all(name in data for name in (b'bmo_invoke', b'bmo_wait')):
        raise ValueError('ABI-TOOLCHAIN: objeto COFF o simbolos de llamada invalidos')
    report = dict(Toolchain='msvc', Stage='COFF', Bytes=len(data),
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
    payload = pack_pe(pe_bytes, abi=1)
    sbef.write_bytes(payload)
    report.update(Stage='SBEF', SBEF=inspect(payload), SBEFSHA256=hashlib.sha256(payload).hexdigest())
    return report, sbef


def verify_msvc_sections(root, out, reference, *, cc, linker, assembler, objcopy, sdk_lib):
    out.mkdir(parents=True, exist_ok=True)
    abi = root/'userspace/runtime/abi/win64'
    obj, pe, sbef = (out/name for name in ('client.obj', 'client.exe', 'client.sbef'))
    subprocess.run([cc, '/nologo', '/std:c++17', '/c', '/O2', '/GS-', '/Zl', f'/Fo{obj}',
                    str(root/'tools/tests/msvc_sections.cpp')], check=True, cwd=out)
    entry = out/'entry.obj'
    subprocess.run([assembler, '--target=x86_64-pc-windows-msvc', '-c', str(abi/'entry.S'),
                    '-o', str(entry)], check=True)
    objects = [entry, obj]
    for unit in ('portal', 'session_clock', 'session_console'):
        target = out/(unit+'.obj')
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-pc-windows-msvc',
                        '--crate-type=lib', '--emit=obj', '-Cpanic=abort', '-Copt-level=2',
                        str(abi/(unit+'.rs')), '-o', str(target)], check=True)
        objects.append(target)
    link_map = out/'client.map'
    subprocess.run([linker, '/nologo', '/machine:x64', '/nodefaultlib', '/subsystem:console',
                    '/entry:bmo_win64_start', '/base:0x3fe00000', '/align:2097152',
                    '/fixed', '/Brepro', '/incremental:no', '/merge:.pdata=.rdata',
                    *('/include:'+name for name in SESSION_EXPORTS.values()),
                    f'/map:{link_map}', f'/out:{pe}', *map(str, objects), sdk_lib], check=True)
    names = ('phase', 'first_ms', 'second_ms', 'scratch', 'written', *SESSION_EXPORTS.values())
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
