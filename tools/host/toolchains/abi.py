"""Build the same BMO-X2 ABI client with ELF toolchains or inspect an MSVC object."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from ..importers.elf import pack_elf
from .msvc import build_msvc, verify_msvc_sections
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
    parser.add_argument('--pe-link', metavar='LINK_EXE', help='Link the MSVC COFF client and Rust Win64 portal into a PE inspection fixture')
    parser.add_argument('--coff-as', default='clang', help='Clang assembler for the Win64 entry and QEMU terminal')
    parser.add_argument('--msvc-sections', action='store_true', help='Test MSVC RX/R/RW and the native Rust clock in QEMU')
    parser.add_argument('--msvc-sdk-lib', default='kernel32.lib', help='Windows x64 SDK import library for the clock fixture')
    parser.add_argument('--reuse', action='store_true', help='Run two distinct embedded SBEFs on the same pages')
    args = parser.parse_args()
    if args.pe_link and args.toolchain != 'msvc':
        parser.error('--pe-link requiere msvc')
    if args.msvc_sections and not (args.toolchain == 'msvc' and args.pe_link and args.abi_run):
        parser.error('--msvc-sections requiere msvc, --pe-link y --abi-run')
    if args.toolchain == 'msvc' and args.abi_run and not args.pe_link:
        parser.error('MSVC --abi-run requiere --pe-link')
    if args.reuse and (not args.abi_run or args.toolchain == 'msvc'):
        parser.error('--reuse requiere --abi-run y un ensamblador ELF64')
    if args.language != 'c' and (not args.abi_run or args.toolchain == 'msvc'):
        parser.error('C++ y Rust requieren --abi-run y un ensamblador ELF64')
    out = ROOT/'build/SBEF/abi'/args.toolchain
    if args.language != 'c':
        out /= args.language
    if args.reuse:
        out /= 'reuse'
    out.mkdir(parents=True, exist_ok=True)
    cc = args.cc or ('cl' if args.toolchain == 'msvc' else args.toolchain)
    if args.toolchain == 'msvc':
        if args.msvc_sections:
            verify_msvc_sections(ROOT, out/'sections-qemu', args.abi_run, cc=cc,
                                 linker=args.pe_link, assembler=args.coff_as, objcopy=args.objcopy,
                                 sdk_lib=args.msvc_sdk_lib)
            return
        report, sbef = build_msvc(out, CLIENT, ABI, ROOT/'tools/doom/complete.S', cc=cc,
                                  linker=args.pe_link, assembler=args.coff_as, qemu=bool(args.abi_run))
        print(json.dumps(report, indent=2), flush=True)
        if sbef is not None:
            subprocess.run([sys.executable, '-B', str(ROOT/'tools/boot/doom_qemu.py'),
                            str(args.abi_run.resolve()), str(sbef), '--toolchain-client', 'msvc'],
                           check=True)
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
    subprocess.run([cc, *target, '-c', str(ABI/'sysv/portal.S'), '-o', str(portal)], check=True, cwd=out)
    subprocess.run([args.objcopy, '-O', 'binary', '--only-section=.text', str(portal), str(raw)], check=True, cwd=out)
    if raw.read_bytes() != bytes.fromhex((ABI/'sysv/portal.hex').read_text(encoding='ascii')):
        raise ValueError('ABI-TOOLCHAIN: los bytes de las puertas difieren del vector')
    script = ROOT/'userspace/sbef.ld'
    objects = [obj, portal]
    if args.abi_run:
        complete = out/'complete.o'
        completion_flags = ['-DBMO_ABI_REUSE'] if args.reuse else []
        subprocess.run([cc, *target, *completion_flags, '-c', str(ROOT/'tools/doom/complete.S'), '-o', str(complete)],
                       check=True, cwd=out)
        script = ROOT / ('tools/boot/abi_reuse.ld' if args.reuse else 'tools/desktop/guest.ld')
        objects.append(complete)
    subprocess.run([args.ld, '-static', '-T', str(script), *map(str, objects),
                    '-o', str(elf)], check=True, cwd=out)
    image = pack_elf(elf.read_bytes(), abi=1)
    sbef.write_bytes(image)
    producer = {'c': args.toolchain, 'cpp': f'{args.toolchain}-cpp', 'rust': 'rust'}[args.language]
    print(json.dumps(dict(Toolchain=producer, Stage='SBEF', PortalBytes=raw.stat().st_size,
                          SHA256=hashlib.sha256(image).hexdigest(), Image=inspect(image)), indent=2), flush=True)
    if args.abi_run:
        command = [sys.executable, '-B', str(ROOT/'tools/boot/doom_qemu.py'),
                   str(args.abi_run.resolve()), str(sbef), '--toolchain-client', producer]
        if args.reuse:
            stage_obj, stage = out/'reuse.o', out/'reuse.bin'
            subprocess.run([cc, *target, '-c', str(ROOT/'tools/boot/abi_reuse.S'), '-o', str(stage_obj)], check=True)
            subprocess.run([args.objcopy, '-O', 'binary', '--only-section=.text', str(stage_obj), str(stage)], check=True)
            second_obj, second_elf, second = out/'second.o', out/'second.elf', out/'second.sbef'
            subprocess.run([cc, *target, *flags, '-DBMO_ABI_SECOND', '-c', str(CLIENT), '-o', str(second_obj)],
                           check=True)
            subprocess.run([args.ld, '-static', '-T', str(script), *map(str, (second_obj, portal, complete)),
                            '-o', str(second_elf)], check=True)
            second.write_bytes(pack_elf(second_elf.read_bytes(), abi=1))
            command.extend(['--reuse', str(stage), str(second)])
        subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
