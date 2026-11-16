"""Export verified QEMU evidence and an optional pre-exit UEFI log separately."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scope import ROOT, workspace


def collect(run, bootlog):
    run = workspace(run)
    result = json.loads((run / 'qemu-results.json').read_text(encoding='utf-8'))
    if result.get('Passed') != result.get('Total') or not result.get('Total'):
        raise ValueError('El run no tiene todas sus comprobaciones aprobadas')
    normal = next(case for case in result['Cases'] if case['Case'] == 'normal')
    report = dict(schema=1, generated_utc=datetime.now(timezone.utc).isoformat(),
                  qemu=dict(run=run.name, result=normal, files=result['files']),
                  physical_runtime=dict(verified=False, reason='No post-ExitBootServices capture supplied'),
                  uefi_log=dict(path=str(bootlog), available=False))
    if bootlog.is_file():
        raw = bootlog.read_bytes()
        if len(raw) > 65536:
            raise ValueError('BOOTLOG excede 64 KiB')
        report['uefi_log'].update(available=True, sha256=hashlib.sha256(raw).hexdigest(),
                                  lines=raw.decode('ascii').splitlines(),
                                  scope='Pre-ExitBootServices only; no HID runtime result')
    return report


def render(report):
    qemu = report['qemu']
    state = qemu['result']
    lines = ['BMO-X2 / REPORTES', '', 'FUENTE: QEMU', 'RUN: ' + qemu['run'],
             'DESCRIPTORES USB: ' + ('COMPROBADOS' if state.get('XhciConfigurationRead') else 'NO ACREDITADOS'),
             'HID CONFIGURADO: ' + ('SI' if state.get('XhciHidConfigured') else 'NO ACREDITADO'),
             'PARADA XHC: ' + ('COMPROBADA' if state.get('XhciControllerStopped') else 'NO ACREDITADA'),
             '', 'FUENTE: BOOTLOG UEFI', 'Solo describe el estado anterior a ExitBootServices.']
    lines.extend(report['uefi_log'].get('lines', ['BOOTLOG no disponible.']))
    lines.extend(['', 'RESULTADO FISICO POSTERIOR: NO CAPTURADO',
                  'SIGUE: registrar la fase visible del panel REPORTES en el proximo boot.',
                  'Una lectura de configuracion no activa interfaces ni endpoints HID.', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--bootlog', type=Path, default=Path('A:/BMO-X2/BOOTLOG.TXT'))
    args = parser.parse_args()
    report = collect(args.run, args.bootlog)
    output = ROOT / 'Reports'
    output.mkdir(exist_ok=True)
    (output / 'latest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    (output / 'latest.txt').write_text(render(report), encoding='ascii')
    print(output / 'latest.txt')


if __name__ == '__main__':
    main()
