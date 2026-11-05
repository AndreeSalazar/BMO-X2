"""Genesis G1: assemble the inherited bootstrap, boot the CASM packet and collect QEMU evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from scope import ROOT, workspace
sys.path.insert(0,str(ROOT/'tools'))
from genesis import check

CASES=['normal','firma','suma','entrada','ausente','excesivo','salida']


def assemble(paths):
    output=bytearray()
    for path in paths:
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            for token in line.split(';',1)[0].split():
                if re.fullmatch(r'[@=][0-9A-Fa-f]+',token):
                    target=int(token[1:],16)
                    if target>1048576 or target<len(output) or (token[0]=='=' and target!=len(output)):
                        raise ValueError('BRIDGE-OFFSET')
                    output.extend(b'\0'*(target-len(output)))
                elif re.fullmatch('[0-9A-Fa-f]{2}',token): output.append(int(token,16))
                else: raise ValueError(f'BRIDGE-TOKEN: {token}')
    if len(output)!=12288 or output[:2]!=b'MZ' or output[0x40:0x44]!=b'PE\0\0':
        raise ValueError('BRIDGE-IMAGE')
    return bytes(output)


def sha(path):
    with path.open('rb') as file: return hashlib.file_digest(file,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--qemu',type=Path,default=Path('C:/Program Files/qemu/qemu-system-x86_64.exe'))
    parser.add_argument('--cases',nargs='+',choices=CASES,default=CASES)
    args=parser.parse_args();run=workspace(args.run)
    check(run)
    if (run/'qemu-run.json').exists(): raise ValueError('Run ya preparado; compilar un run nuevo para otra ejecucion')
    qemu=args.qemu.resolve();share=qemu.parent/'share'
    for path in [qemu,share/'edk2-x86_64-code.fd',share/'edk2-i386-vars.fd']:
        if not path.is_file(): raise ValueError(f'Falta herramienta: {path}')
    bridge=ROOT/'kernel/boot/bridge'
    paths=[bridge/name for name in ['cabecera.hex','entrada.hex','datos.hex','fuente.hex']]
    image=assemble(paths)
    efi=run/'build/Puente_Metal/EFI/BOOT/BOOTX64.EFI';efi.parent.mkdir(parents=True,exist_ok=True);efi.write_bytes(image)
    packet=run/'build/Puente_Metal/METAL/INICIO.X86';packet.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(run/'INICIO.X86',packet)
    version=subprocess.check_output([str(qemu),'--version'],text=True).splitlines()[0]
    record=dict(schema=1,milestone='Genesis G1',qemu=version,accelerator='tcg',cpu='qemu64',ram_mib=256,
                cases=args.cases,bridge_sha256=sha(efi),bridge_bytes=len(image),packet_sha256=sha(packet),
                inputs={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
                tools={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(Path(__file__).resolve().parent.iterdir()) if p.suffix in {'.py','.ps1'}},
                firmware={p.name:sha(p) for p in [share/'edk2-x86_64-code.fd',share/'edk2-i386-vars.fd']},
                scope='VM snapshot images only; inherited UEFI bootstrap, CASM payload; no physical boot or autonomous kernel')
    (run/'qemu-run.json').write_text(json.dumps(record,indent=2)+'\n',encoding='ascii',newline='\n')
    scripts=Path(__file__).resolve().parent
    shell=shutil.which('pwsh')
    if not shell: raise ValueError('Falta PowerShell 7')
    subprocess.run([shell,'-NoProfile','-File',str(scripts/'disk.ps1'),'-OutputRoot',str(run),'-Programa','INICIO.X86','-GPT'],check=True,cwd=run,timeout=60)
    for case in args.cases:
        subprocess.run([sys.executable,'-B',str(scripts/'prepare.py'),'--workspace',str(run),'--caso',case],check=True,cwd=run,timeout=30)
    result=subprocess.run([sys.executable,'-B','-u',str(scripts/'probe.py'),'--workspace',str(run),'--qemu',str(qemu),'--casos',*args.cases],cwd=run,timeout=600)
    report=run/'build/puente-test-results.json'
    if report.is_file():
        data=json.loads(report.read_text(encoding='utf-8-sig'))
        data.update(schema=1,evidence='QEMU',milestone='Genesis G1',physical_boot=False,autonomous_kernel=False,
                    body_bytes=22,packet_bytes=46,bridge_bytes=len(image),run=run.name,packet_sha256=sha(packet),
                    qemu=version,source_sha256=sha(run/'source.casm'),case_scope='UEFI bootstrap and payload; rejects packages and injected stale MapKey, not arbitrary invalid kernel contexts')
        (run/'qemu-results.json').write_text(json.dumps(data,indent=2)+'\n',encoding='ascii',newline='\n')
        print(json.dumps(data,indent=2),flush=True)
    if result.returncode: raise ValueError('Genesis G1 fallo; conservar el run para inspeccion')
    if not report.is_file(): raise ValueError('QEMU no produjo informe')


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        raise SystemExit(f'RED [GENESIS-QEMU] {error}') from error
