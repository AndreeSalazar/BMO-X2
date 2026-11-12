"""Build the same BMO-X2 ABI client with ELF toolchains or inspect an MSVC object."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from sbef_host.elf import pack_elf
from sbef_host.format import inspect


ROOT = Path(__file__).resolve().parents[1]
ABI = ROOT/'userspace/runtime/abi'
CLIENT = ROOT/'tools/tests/abi_client.c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('toolchain', choices=['clang', 'gcc', 'msvc'])
    parser.add_argument('--cc')
    parser.add_argument('--ld', default='ld.lld')
    parser.add_argument('--objcopy', default='llvm-objcopy')
    args = parser.parse_args()
    out = ROOT/'build/SBEF/abi'/args.toolchain
    out.mkdir(parents=True, exist_ok=True)
    cc = args.cc or ('cl' if args.toolchain == 'msvc' else args.toolchain)
    if args.toolchain == 'msvc':
        obj = out/'client.obj'
        subprocess.run([cc, '/nologo', '/std:c11', '/c', '/O2', '/GS-', '/Zl',
                        f'/Fo{obj}', str(CLIENT)], check=True, cwd=out)
        data = obj.read_bytes()
        if data[:2] != b'\x64\x86' or not all(name in data for name in (b'bmo_invoke', b'bmo_wait')):
            raise ValueError('ABI-TOOLCHAIN: objeto COFF o simbolos de llamada invalidos')
        print(json.dumps(dict(Toolchain='msvc', Stage='COFF', Bytes=len(data),
                              SHA256=hashlib.sha256(data).hexdigest()), indent=2))
        return

    target = ['--target=x86_64-unknown-none-elf'] if args.toolchain == 'clang' else ['-m64']
    flags = ['-O2', '-ffreestanding', '-fno-pic', '-fno-pie', '-fno-stack-protector',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables']
    obj, portal, raw, elf, sbef = (out/name for name in ('client.o', 'portal.o', 'portal.bin', 'client.elf', 'client.sbef'))
    subprocess.run([cc, *target, *flags, '-c', str(CLIENT), '-o', str(obj)], check=True, cwd=out)
    subprocess.run([cc, *target, '-c', str(ABI/'portal.S'), '-o', str(portal)], check=True, cwd=out)
    subprocess.run([args.objcopy, '-O', 'binary', '--only-section=.text', str(portal), str(raw)], check=True, cwd=out)
    if raw.read_bytes() != bytes.fromhex((ABI/'portal.hex').read_text(encoding='ascii')):
        raise ValueError('ABI-TOOLCHAIN: los bytes de las puertas difieren del vector')
    subprocess.run([args.ld, '-static', '-T', str(ROOT/'userspace/sbef.ld'),
                    str(obj), str(portal), '-o', str(elf)], check=True, cwd=out)
    image = pack_elf(elf.read_bytes(), abi=1)
    sbef.write_bytes(image)
    print(json.dumps(dict(Toolchain=args.toolchain, Stage='SBEF', PortalBytes=raw.stat().st_size,
                          SHA256=hashlib.sha256(image).hexdigest(), Image=inspect(image)), indent=2))


if __name__ == '__main__':
    main()
