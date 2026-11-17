"""Build the COFF client and its freestanding Win64 ABI fixture."""
import hashlib
import subprocess

from ..importers.pe import pack_pe, probe_pe
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
