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
from cpu_config import write_config
sys.path.insert(0,str(ROOT/'tools'))
from genesis import check as genesis_check
sys.path.insert(0,str(ROOT/'CASM'))
from stop_verify import check as stop_check, CPU_PROFILE, CONTEXT_PROFILE, FAULT_PROFILE, MEMORY_PROFILE, CYCLE_PROFILE, PAGING_PROFILE
from splash_verify import check as splash_check, PROFILE as SPLASH_PROFILE, HD_PROFILE


def check(run):
    profile = (run/'profile.txt').read_text(encoding='utf-8-sig').strip() if (run/'profile.txt').exists() else 'metal64-0.2'
    if profile == 'ring0-stop-0.1': return stop_check(run)
    if profile == CPU_PROFILE: return stop_check(run, identify=True)
    if profile == CONTEXT_PROFILE: return stop_check(run, context=True)
    if profile == FAULT_PROFILE: return stop_check(run, fault=True)
    if profile == MEMORY_PROFILE: return stop_check(run, memory=True)
    if profile == CYCLE_PROFILE: return stop_check(run, cycle=True)
    if profile == PAGING_PROFILE: return stop_check(run, paging=True)
    if profile == SPLASH_PROFILE: return splash_check(run)
    if profile == HD_PROFILE: return splash_check(run, hd=True)
    if profile != 'metal64-0.2': raise ValueError('Perfil desconocido')
    return genesis_check(run)

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
    parser.add_argument('--powershell',type=Path,help='Use the same PowerShell executable as the calling build')
    parser.add_argument('--cases',nargs='+',choices=CASES+['contexto'],default=CASES)
    parser.add_argument('--cpu', choices=['qemu64', 'Nehalem'], default='qemu64')
    parser.add_argument('--profile',choices=['metal64-0.2','ring0-stop-0.1',CPU_PROFILE,CONTEXT_PROFILE,FAULT_PROFILE,MEMORY_PROFILE,CYCLE_PROFILE,PAGING_PROFILE,SPLASH_PROFILE,HD_PROFILE],default='metal64-0.2')
    args=parser.parse_args();run=workspace(args.run)
    identify=args.profile==CPU_PROFILE
    stack=args.profile==CONTEXT_PROFILE
    fault=args.profile==FAULT_PROFILE
    memory_probe=args.profile==MEMORY_PROFILE
    cycle=args.profile==CYCLE_PROFILE
    paging=args.profile==PAGING_PROFILE
    splash=args.profile in (SPLASH_PROFILE,HD_PROFILE)
    stop=args.profile!='metal64-0.2'
    frozen_profile=(run/'profile.txt').read_text(encoding='utf-8-sig').strip() if (run/'profile.txt').exists() else 'metal64-0.2'
    if frozen_profile!=args.profile: raise ValueError('Perfil distinto al run congelado')
    if identify and args.cases != ['normal']: raise ValueError('La identificacion requiere el caso normal')
    if splash and args.cases != ['normal']: raise ValueError('El splash requiere el caso normal')
    checks_handoff = stack or fault or memory_probe or cycle or paging
    if checks_handoff and args.cases != ['normal','contexto']: raise ValueError('La prueba exige contexto valido e invalido')
    if not checks_handoff and 'contexto' in args.cases: raise ValueError('El caso contexto exige una prueba de entrega')
    milestone='Ring0 own page tables' if paging else 'Ring0 physical frame lifecycle' if cycle else 'Ring0 physical frame' if memory_probe else 'Ring0 invalid opcode handler' if fault else 'Ring0 cat splash' if splash else 'Ring0 handoff and stack' if stack else 'Ring0 CPU identification' if identify else ('Ring0 stop S1' if stop else 'Genesis G1')
    ram_mib=1024 if splash else 256
    verified = check(run)
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
    shell=str(args.powershell.resolve()) if args.powershell else (shutil.which('pwsh') or shutil.which('powershell.exe'))
    if not shell or not Path(shell).is_file(): raise ValueError('Falta PowerShell 5.1 o 7')
    shell_version=subprocess.check_output([shell,'-NoProfile','-NonInteractive','-Command','$PSVersionTable.PSVersion.ToString()'],text=True).strip()
    record=dict(schema=1,milestone=milestone,qemu=version,accelerator='tcg',cpu=args.cpu,ram_mib=ram_mib,
                powershell=shell_version,
                cases=args.cases,bridge_sha256=sha(efi),bridge_bytes=len(image),packet_sha256=sha(packet),
                inputs={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
                tools={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(Path(__file__).resolve().parent.iterdir()) if p.suffix in {'.py','.ps1'}},
                firmware={p.name:sha(p) for p in [share/'edk2-x86_64-code.fd',share/'edk2-i386-vars.fd']},
                scope='VM snapshot images only; inherited UEFI bootstrap, CASM payload; no physical boot or autonomous kernel')
    (run/'qemu-run.json').write_text(json.dumps(record,indent=2)+'\n',encoding='ascii',newline='\n')
    scripts=Path(__file__).resolve().parent
    subprocess.run([shell,'-NoProfile','-NonInteractive','-File',str(scripts/'disk.ps1'),'-OutputRoot',str(run),'-Programa','INICIO.X86','-GPT'],check=True,cwd=run,timeout=60)
    for case in args.cases:
        subprocess.run([sys.executable,'-B',str(scripts/'prepare.py'),'--workspace',str(run),'--caso',case],check=True,cwd=run,timeout=30)
    probe_flags = ['--halt', '--identify'] if identify else (['--halt'] if stop else [])
    if stack:
        probe_flags.append('--stack')
    if fault:
        probe_flags.append('--fault')
    if memory_probe:
        probe_flags.append('--memory')
    if cycle:
        probe_flags.append('--frame-cycle')
    if paging:
        probe_flags.append('--paging')
    if splash:
        probe_flags.append('--splash')
    if args.profile == HD_PROFILE:
        probe_flags.append('--splash-hd')
    result=subprocess.run([sys.executable,'-B','-u',str(scripts/'probe.py'),'--workspace',str(run),'--qemu',str(qemu),'--cpu',args.cpu,'--ram-mib',str(ram_mib),'--casos',*args.cases,*probe_flags],cwd=run,timeout=600)
    report=run/'build/puente-test-results.json'
    if report.is_file():
        data=json.loads(report.read_text(encoding='utf-8-sig'))
        data.update(schema=1,evidence='QEMU',milestone=milestone,physical_boot=False,autonomous_kernel=False,
                    body_bytes=len(packet.read_bytes())-24,packet_bytes=packet.stat().st_size,bridge_bytes=len(image),run=run.name,packet_sha256=sha(packet),
                    qemu=version,source_sha256=sha(run/'source.casm'),
                    case_scope='Own CR3, supervisor mapping and user read-only NX alias under QEMU' if paging else
                    'Single frame ownership, scrub and reuse under QEMU' if cycle else
                    'Physical frame marker and null handoff rejection under QEMU' if memory_probe else
                    'Own IDT and controlled #UD; null handoff rejection under QEMU' if fault else
                    'Three verified framebuffer frames in Ring 0 under QEMU' if splash else
                    'Stack selection and rejection of null RDI under QEMU' if stack else
                    'CPUID leaf 0 and own halt under QEMU' if identify else
                    'UEFI bootstrap and payload; rejects packages and injected stale MapKey, not arbitrary invalid kernel contexts')
        (run/'qemu-results.json').write_text(json.dumps(data,indent=2)+'\n',encoding='ascii',newline='\n')
        print(json.dumps(data,indent=2),flush=True)
    if result.returncode: raise ValueError(f'{milestone} fallo; conservar el run para inspeccion')
    if not report.is_file(): raise ValueError('QEMU no produjo informe')
    if identify:
        print(f'Perfil observado: {write_config(run, data, record, verified)}')


if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        raise SystemExit(f'RED [GENESIS-QEMU] {error}') from error
