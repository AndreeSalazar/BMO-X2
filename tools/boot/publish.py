"""Publish a small, checked evidence snapshot; keep VM images and raw dumps in build/."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from scope import ROOT,workspace
from wake import sha,check,CASES


def publish(run):
    run=workspace(run);check(run)
    report=json.loads((run/'qemu-results.json').read_text(encoding='ascii'))
    environment=json.loads((run/'qemu-run.json').read_text(encoding='ascii'))
    if report['Passed']!=7 or report['Total']!=7 or {c['Case'] for c in report['Cases']}!=set(CASES) or not all(c['Passed'] for c in report['Cases']):
        raise ValueError('QEMU-EVIDENCE: faltan casos aprobados')
    normal=next(c for c in report['Cases'] if c['Case']=='normal')
    if not normal['BootServicesExited'] or not normal['PayloadReturned'] or normal['Ring']!=0 or not normal['OwnFramebufferTextVerified']:
        raise ValueError('QEMU-EVIDENCE: ejecucion normal incompleta')
    if report['packet_sha256']!=sha(run/'INICIO.X86') or report['source_sha256']!=sha(ROOT/'kernel/boot/genesis/main.casm'):
        raise ValueError('QEMU-EVIDENCE: fuente o paquete distintos')
    if (run/'build/puente-normal-code.bin').read_bytes()!=(run/'INICIO.X86').read_bytes()[24:]:
        raise ValueError('QEMU-EVIDENCE: bytes cargados distintos')
    for group in ['inputs','tools']:
        for path,digest in environment[group].items():
            file=(ROOT/path).resolve()
            if not file.is_relative_to(ROOT) or sha(file)!=digest: raise ValueError(f'QEMU-EVIDENCE: cambio la entrada {path}')
    target=ROOT/'kernel/boot/genesis/evidence';target.mkdir(parents=True,exist_ok=True)
    files=[(run/'qemu-results.json','qemu.json'),(run/'qemu-run.json','environment.json'),
           (run/'build/puente-normal.png','normal.png'),(run/'build/puente-normal-registers.txt','registers.txt')]
    entries=[]
    for source,name in files:
        shutil.copyfile(source,target/name)
        entries.append(dict(path=name,bytes=source.stat().st_size,sha256=sha(source)))
    (target/'manifest.json').write_text(json.dumps(dict(schema=1,run=run.name,evidence='QEMU',files=entries,physical_boot=False),indent=2)+'\n',encoding='ascii',newline='\n')
    print(f'Evidencia de siete casos conservada en {target}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);args=p.parse_args()
    try:publish(args.run)
    except (OSError,ValueError,KeyError) as error:raise SystemExit(f'RED [QEMU-EVIDENCE] {error}') from error
