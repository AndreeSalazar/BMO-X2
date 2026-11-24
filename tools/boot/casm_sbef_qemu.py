"""Compare the CASM Native SBEF validator with HOST inside a diskless Linux VM."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from scope import ROOT

sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'CASM/native')]
from host.diagnostics import Rejection
from host.sbef.format import encode_header, inspect
from freestanding import convert, validate
from verify import audit


SOURCE = ROOT / 'kernel/loader/sbef_validate.casm'
ENTRY = SOURCE.with_name('sbef_validate_entry.casm')
HARNESS = ROOT / 'tools/tests/casm_sbef_freestanding.c'
INPUT_MARKER = 0x32464542534f4d42
CHECKS = (
    ('SBEF-SIZE', 'file'), ('SBEF-HEADER', 'signature'), ('SBEF-HEADER', 'architecture'),
    ('SBEF-HEADER', 'reserved'), ('SBEF-HEADER', 'flags'), ('SBEF-ISA-PROFILE', 'isa_profile'),
    ('SBEF-HEADER', 'format_version'), ('SBEF-HEADER', 'abi_version'), ('SBEF-TABLE', 'region_count'),
    ('SBEF-SIZE', 'file_size'), ('SBEF-REGION', 'reserved'), ('SBEF-PERMISSIONS', 'permissions'),
    ('SBEF-REGION', 'memory_size'), ('SBEF-VIRTUAL-RANGE', 'virtual_address'),
    ('SBEF-FILE-RANGE', 'file_offset'), ('SBEF-FILE-RANGE', 'file_size'),
    ('SBEF-TRAILING-DATA', 'payload'), ('SBEF-ENTRY', 'entry'),
)


def samples():
    base = 0x40000000
    image = encode_header(1, 2, 97, base)
    image += struct.pack('<QIIIIQ', base, 96, 1, 4096, 5, 0)
    image += struct.pack('<QIIIIQ', base + 4096, 97, 0, 4096, 6, 0)
    image += b'\xc3'
    eight = encode_header(1, 8, 289, base)
    eight += struct.pack('<QIIIIQ', base, 288, 1, 4096, 5, 0)
    for index in range(1, 8):
        eight += struct.pack('<QIIIIQ', base + index * 8192, 289, 0, 4096, 6, 0)
    yield 'v2-v1', image
    yield 'v1-legacy', encode_header(1, 2, 97, base, format_version=1) + image[32:]
    yield 'v2-v4-declared', encode_header(1, 2, 97, base, isa_profile='x86-64-v4') + image[32:]
    yield 'eight-regions', eight + b'\xc3'
    yield 'short-header', image[:31]
    yield 'over-file-limit', image.ljust(1048577, b'\0')
    yield 'short-table', image[:64]
    yield 'legacy-flag', encode_header(1, 2, 97, base, format_version=1)[:24] + image[24:]
    yield 'trailing-byte', image[:12] + struct.pack('<I', 98) + image[16:] + b'\0'
    for name, offset, width, value in (
        ('signature', 0, 'I', 0), ('version', 4, 'H', 3), ('architecture', 8, 'H', 3),
        ('reserved', 28, 'I', 1), ('isa-id', 24, 'I', 5), ('abi', 6, 'H', 2),
        ('region-count', 10, 'H', 9), ('file-length', 12, 'I', 98),
        ('entry', 16, 'Q', base + 1), ('region-reserved', 88, 'Q', 1),
        ('write-execute', 84, 'I', 7), ('zero-memory', 80, 'I', 0),
        ('overlap', 64, 'Q', base), ('unaligned', 64, 'Q', base + 4097),
        ('high-address', 64, 'Q', 0xfffffffffffff000), ('window-end', 64, 'Q', 0x41000000),
        ('window-overflow', 80, 'I', 0xffffffff), ('file-offset', 72, 'I', 96),
        ('file-overrun', 76, 'I', 1),
    ):
        changed = bytearray(image)
        struct.pack_into('<' + width, changed, offset, value)
        yield name, changed


def newc(files):
    archive = bytearray()
    for inode, (name, mode, data) in enumerate([*files, ('TRAILER!!!', 0, b'')], 1):
        name = name.encode('ascii') + b'\0'
        fields = (inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0)
        archive += b'070701' + ''.join(f'{value:08x}' for value in fields).encode('ascii') + name
        archive += bytes(-len(archive) % 4)
        archive += data
        archive += bytes(-len(archive) % 4)
    return archive


INIT = r"""
static long sc(long n,long a,long b,long c,long d) {
    register long r10 __asm__("r10")=d;
    __asm__ volatile("syscall" : "+a"(n) : "D"(a),"S"(b),"d"(c),"r"(r10)
                     : "rcx","r11","memory");
    return n;
}
static int run(const char *path, const char *input, const char *out, const char *hex) {
    const char *args[]={path,input,out,hex,0};
    int status=-1;
    long pid=sc(57,0,0,0,0);
    if(pid==0) {
        sc(59,(long)path,(long)args,0,0);
        sc(60,127,0,0,0);
    }
    return pid<0 || sc(61,pid,(long)&status,0,0)!=pid || status!=0;
}
static int report_elf(void) {
    static const char digits[]="0123456789abcdef";
    unsigned char bytes[256];
    char hex[512];
    long fd=sc(2,(long)"/validator",0,0,0);
    if(fd<0 || sc(1,1,(long)"BMO_ELF ",8,0)!=8) return 1;
    for(;;) {
        long count=sc(0,fd,(long)bytes,sizeof bytes,0);
        if(count<0) return 1;
        if(count==0) break;
        for(long i=0;i<count;i++) {
            hex[2*i]=digits[bytes[i]>>4];
            hex[2*i+1]=digits[bytes[i]&15];
        }
        if(sc(1,1,(long)hex,2*count,0)!=2*count) return 1;
    }
    return sc(1,1,(long)"\n",1,0)!=1;
}
void _start(void) {
    if(run("/casmc","/validator.casm","/validator","/validator.hex")) goto done;
    if(report_elf()) goto done;
#ifndef COMPILE_ONLY
    for(unsigned i=0;i<CASE_COUNT;i++) {
        char name[]="/case00";
        name[5]='0'+i/10;
        name[6]='0'+i%10;
        sc(1,1,(long)"BMO_SBEF ",9,0);
        if(run("/validator",name,"unused","unused")) goto done;
    }
#endif
    sc(1,1,(long)"BMO_COMPLETE\n",13,0);
done:
    sc(169,0xfee1dead,672274793,0x4321fedc,0);
    for(;;) sc(34,0,0,0,0);
}
"""


def boot_guest(args, run, name, source, defines, files):
    init, initrd, log = (run / (name + suffix) for suffix in ('.init', '.cpio', '.log'))
    subprocess.run([args.clang, '--target=x86_64-unknown-linux-gnu', f'--ld-path={args.lld}',
                    '-nostdlib', '-static', '-ffreestanding', '-fno-stack-protector', '-Os',
                    '-Wl,-e,_start,--image-base=0x2000000',
                    *(f'-D{key}={value}' for key, value in defines.items()),
                    '-o', init, source], check=True)
    initrd.write_bytes(newc([*files, ('bmo-init', 0o100755, init.read_bytes())]))
    with log.open('wb') as output:
        subprocess.run([args.qemu, '-m', '256', '-kernel', args.kernel, '-initrd', initrd,
                        '-append', 'rdinit=/bmo-init console=ttyS0 quiet loglevel=0 panic=-1',
                        '-display', 'none', '-monitor', 'none', '-serial', 'stdio',
                        '-nic', 'none', '-no-reboot'], stdout=output, stderr=subprocess.STDOUT,
                       check=True, timeout=90)
    serial = log.read_text(encoding='ascii', errors='replace')
    if 'BMO_COMPLETE' not in serial.splitlines():
        raise ValueError(f'El invitado CASM no termino. Ver {log}')
    return serial


def run_freestanding(args, run, elf, cases):
    module = convert(elf)
    validate(module)
    text, data = module['segments']
    text_bytes, data_bytes = (bytes.fromhex(segment['hex']) for segment in (text, data))
    # Check the public input slot from initialized data, before calling native code.
    if data_bytes != bytes(24 + 296 * 8) + struct.pack('<Q', INPUT_MARKER):
        raise ValueError('Cambio el contrato de memoria del validador CASM')
    files = [*cases, ('text', 0o100644, text_bytes), ('data', 0o100644, data_bytes)]
    defines = dict(CASE_COUNT=len(cases), ENTRY=module['entry'], STACK_BYTES=module['stack_bytes'],
                   TEXT_ADDRESS=text['address'], TEXT_BYTES=len(text_bytes),
                   DATA_ADDRESS=data['address'], DATA_BYTES=len(data_bytes), DATA_MEMORY=data['memory_bytes'],
                   INPUT_MARKER=INPUT_MARKER)
    serial = boot_guest(args, run, 'freestanding', HARNESS, defines, files)
    resident = re.findall(r'^BMO_RW_RESIDENT (\d+)$', serial, re.M)
    if len(resident) != 1 or not 1 <= int(resident[0]) <= data['memory_bytes'] // 4096:
        raise ValueError(f'El invitado no devolvio una medida de residencia valida. Ver {run}')
    (run / 'validator.module.json').write_text(json.dumps(module, indent=2) + '\n', encoding='ascii')
    return serial, dict(linux_services=module['linux_services'], text_sha256=module['text_sha256'],
                        data_sha256=module['data_sha256'], rx_bytes=len(text_bytes),
                        initialized_data_bytes=len(data_bytes), rw_nx_virtual_bytes=data['memory_bytes'],
                        rw_nx_resident_pages_after_cases=int(resident[0]),
                        stack_bytes=module['stack_bytes'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--casmc', type=Path, required=True)
    parser.add_argument('--qemu', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--lld', type=Path, required=True)
    parser.add_argument('--freestanding', action='store_true',
                        help='Use the independently verified module without Linux services')
    args = parser.parse_args()
    build = ROOT / 'build/CASM'
    build.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-casm-sbef-', dir=build))
    entry = ENTRY.read_bytes() if args.freestanding else (
        b'u64 casm_main() { u64 n=0; n=input(sbef_input); print(validate_sbef(n)); return 0; }\n')
    source = SOURCE.read_bytes() + b'\n' + entry
    files = [('casmc', 0o100755, args.casmc.read_bytes()), ('validator.casm', 0o100644, source)]
    audit(files[0][2])
    expected, cases = [], []
    for index, (name, image) in enumerate(samples()):
        receipt = 0
        try:
            inspect(image)
        except Rejection as error:
            receipt = (1 + CHECKS.index((error.code, error.field))) * 2097152 + error.offset
        expected.append(dict(case=name, receipt=receipt))
        cases.append((f'case{index:02}', 0o100644, struct.pack('<Q', len(image)) + image[:288]))
    expected.append(dict(case='truncated-envelope', receipt=19 * 2097152))
    cases.append((f'case{len(expected)-1:02}', 0o100644, struct.pack('<Q', 500)))
    init_src = run / 'init.c'
    init_src.write_text(INIT, encoding='ascii')
    print(f'Run: {run}', flush=True)
    defines = dict(COMPILE_ONLY=1) if args.freestanding else dict(CASE_COUNT=len(cases))
    serial = boot_guest(args, run, 'compile', init_src, defines, files if args.freestanding else files + cases)
    elf_match = re.findall(r'^BMO_ELF ([0-9a-f]+)$', serial, re.M)
    if len(elf_match) != 1:
        raise ValueError(f'El invitado no devolvio el ELF compilado. Ver {run / "compile.log"}')
    elf = bytes.fromhex(elf_match[0])
    audit(elf)
    module_report = {}
    if args.freestanding:
        serial, module_report = run_freestanding(args, run, elf, cases)
    receipts = [int(value) for value in re.findall(r'^BMO_SBEF (\d+)\s*$', serial, re.M)]
    if len(receipts) != len(expected):
        raise ValueError(f'El ensayo CASM no devolvio todos los recibos. Ver {run}')
    for case, observed in zip(expected, receipts, strict=True):
        if observed != case['receipt']:
            raise ValueError(f'{case["case"]}: CASM {observed}, esperado {case["receipt"]}. Ver {run}')
    (run / 'validator.elf').write_bytes(elf)
    report = dict(run=run.name, evidence='QEMU Linux, CASM Native x86-64 program running in user mode',
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  build_source_sha256=hashlib.sha256(source).hexdigest(),
                  compiler_sha256=hashlib.sha256(files[0][2]).hexdigest(),
                  verified_elf_sha256=hashlib.sha256(elf).hexdigest(), elf_bytes=len(elf),
                  passed=len(receipts), total=len(expected), cases=expected)
    if module_report:
        report['freestanding'] = module_report
    (run / 'qemu-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='ascii')
    print(f'CASM y HOST: {len(receipts)} recibos comprobados')


if __name__ == '__main__':
    main()
