"""Build the same BMO-X2 ABI client with ELF toolchains or inspect an MSVC object."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from ..importers.elf import pack_elf
from ..sbef.format import inspect


ROOT = Path(__file__).resolve().parents[3]
ABI = ROOT/'userspace/runtime/abi'
CLIENT = ROOT/'tools/tests/abi_client.c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('toolchain', choices=['clang', 'gcc', 'msvc'])
    parser.add_argument('--cc')
    parser.add_argument('--ld', default='ld.lld')
    parser.add_argument('--objcopy', default='llvm-objcopy')
    parser.add_argument('--abi-run', type=Path, help='Execute the common client in the CASM ABI QEMU fixture')
    parser.add_argument('--language', choices=['c', 'cpp', 'rust'], default='c')
    args = parser.parse_args()
    if args.language != 'c' and (not args.abi_run or args.toolchain == 'msvc'):
        parser.error('C++ y Rust requieren --abi-run y un ensamblador ELF64')
    out = ROOT/'build/SBEF/abi'/args.toolchain
    if args.language != 'c':
        out /= args.language
    out.mkdir(parents=True, exist_ok=True)
    cc = args.cc or ('cl' if args.toolchain == 'msvc' else args.toolchain)
    if args.toolchain == 'msvc':
        if args.abi_run:
            parser.error('--abi-run requires GCC or Clang ELF64')
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
    if args.abi_run:
        flags += ['-DBMO_ABI_QEMU']
        obj, elf, sbef = (out / name for name in ('client-qemu.o', 'client-qemu.elf', 'client-qemu.sbef'))
    if args.language == 'rust':
        subprocess.run(['rustc', '--edition=2024', '--target=x86_64-unknown-none', '--emit=obj',
                        '-Cpanic=abort', '-Copt-level=s', '-Crelocation-model=static',
                        '-Cforce-unwind-tables=no', str(CLIENT.with_suffix('.rs')), '-o', str(obj)],
                       check=True, cwd=out)
    else:
        language = ['-x', 'c++', '-fno-exceptions', '-fno-rtti'] if args.language == 'cpp' else []
        subprocess.run([cc, *target, *flags, *language, '-c', str(CLIENT), '-o', str(obj)], check=True, cwd=out)
    subprocess.run([cc, *target, '-c', str(ABI/'portal.S'), '-o', str(portal)], check=True, cwd=out)
    subprocess.run([args.objcopy, '-O', 'binary', '--only-section=.text', str(portal), str(raw)], check=True, cwd=out)
    if raw.read_bytes() != bytes.fromhex((ABI/'portal.hex').read_text(encoding='ascii')):
        raise ValueError('ABI-TOOLCHAIN: los bytes de las puertas difieren del vector')
    script = ROOT/'userspace/sbef.ld'
    objects = [obj, portal]
    if args.abi_run:
        complete = out/'complete.o'
        subprocess.run([cc, *target, '-c', str(ROOT/'tools/doom/complete.S'), '-o', str(complete)],
                       check=True, cwd=out)
        script = ROOT/'tools/desktop/guest.ld'
        objects.append(complete)
    subprocess.run([args.ld, '-static', '-T', str(script), *map(str, objects),
                    '-o', str(elf)], check=True, cwd=out)
    image = pack_elf(elf.read_bytes(), abi=1)
    sbef.write_bytes(image)
    producer = {'c': args.toolchain, 'cpp': f'{args.toolchain}-cpp', 'rust': 'rust'}[args.language]
    print(json.dumps(dict(Toolchain=producer, Stage='SBEF', PortalBytes=raw.stat().st_size,
                          SHA256=hashlib.sha256(image).hexdigest(), Image=inspect(image)), indent=2), flush=True)
    if args.abi_run:
        subprocess.run([sys.executable, '-B', str(ROOT/'tools/boot/doom_qemu.py'),
                        str(args.abi_run.resolve()), str(sbef), '--toolchain-client', producer], check=True)


if __name__ == '__main__':
    main()
