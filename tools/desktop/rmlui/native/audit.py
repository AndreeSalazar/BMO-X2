"""Measure actual native ELF libraries and unresolved services, never claim a guest run."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'build/rmlui-native'
LLVM = Path(os.environ['ProgramFiles']) / 'LLVM/bin'
sys.path.insert(0, str(ROOT / 'tools'))
from host.importers.elf import pack_elf
from host.diagnostics import Rejection


def archive_members(path):
    data = path.read_bytes()
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('Not a static archive: ' + str(path))
    at, count = 8, 0
    while at < len(data):
        header = data[at:at+60]
        if len(header) != 60 or header[58:] != b'`\n':
            raise ValueError('Invalid archive header')
        size = int(header[48:58])
        body = data[at+60:at+60+size]
        if len(body) != size:
            raise ValueError('Truncated archive member')
        name = header[:16].strip()
        if name not in (b'/', b'//', b'/SYM64/'):
            if name.startswith(b'#1/'):
                body = body[int(name[3:]):]
            if (body[:6] != b'\x7fELF\x02\x01' or len(body) < 64
                    or struct.unpack_from('<HH', body, 16) != (1, 62)):
                raise ValueError('Archive contains a non-ELF64 x86-64 object: ' + str(path))
            count += 1
        at += 60 + size + (size & 1)
    if at != len(data) or not count:
        raise ValueError('Invalid/empty native archive')
    return count


def main():
    paths = [OUT / 'engine/librmlui.a',
             OUT / 'engine/freetype/libfreetype.a', OUT / 'runtime/lib/libc++.a']
    libraries = {str(p.relative_to(ROOT)).replace('\\', '/'):
                 dict(bytes=p.stat().st_size, elf64_objects=archive_members(p),
                      sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
    # libc++.a already embeds libc++abi with LIBCXX_ENABLE_STATIC_ABI_LIBRARY.
    combined = OUT / 'rmlui-native.o'
    subprocess.run([str(LLVM / 'ld.lld.exe'), '-r', '--whole-archive', *map(str, paths),
                    '--no-whole-archive', '-o', str(combined)], check=True)
    output = subprocess.check_output([str(LLVM / 'llvm-nm.exe'), '--undefined-only', str(combined)], text=True)
    (OUT / 'unresolved.txt').write_text(output, encoding='ascii')
    symbols = sorted({line.split()[-1] for line in output.splitlines() if line.split()})
    forbidden = [s for s in symbols if s.startswith(('__imp_', '__Cxx', '_Unwind_', '__tls_', 'pthread_'))
                 or s in ('syscall', '__syscall', '__stack_chk_fail')]
    if forbidden:
        raise ValueError('Unexpected platform dependency: ' + ', '.join(forbidden))
    try:
        pack_elf(combined.read_bytes(), abi=1)
    except Rejection as error:
        admission = error.report()
        if admission['Code'] != 'ELF-HEADER':
            raise ValueError('Unexpected rejection for relocatable object: ' + repr(admission))
    else:
        raise ValueError('HOST accepted a relocatable object as an executable')
    report = dict(schema=1, evidence='HOST-cross-compile', target='x86_64-unknown-none-elf',
                  executable=False, sbef=False, ring3_ready=False, libraries=libraries,
                  compiler=subprocess.check_output([str(LLVM / 'clang++.exe'), '--version'], text=True).splitlines()[0],
                  exceptions=False, rtti=False, threads=False, localization=False,
                  relocatable_bytes=combined.stat().st_size, unresolved_symbols=symbols,
                  sbef_rejection=admission,
                  note='Real RmlUi/FreeType/libc++ objects. Unresolved C services must be implemented before an executable or SBEF exists.')
    (OUT / 'native-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
