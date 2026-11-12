"""Read a frozen metal64 run only after independently checking its source, IR and bytes."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'CASM'))
from verify import verify


def render(run):
    profile = (run/'profile.txt').read_text(encoding='utf-8-sig').strip() if (run/'profile.txt').exists() else 'metal64-0.2'
    if profile in ('ring0-stop-0.1', 'ring0-cpu-0.1', 'ring0-context-0.1'):
        from stop_verify import verify as selected_verify
        options = {'identify': profile == 'ring0-cpu-0.1', 'context': profile == 'ring0-context-0.1'}
    elif profile == 'metal64-0.2':
        selected_verify = verify
        options = {}
    else:
        raise ValueError('Perfil desconocido')
    packet, report = selected_verify(run/'source.casm', run/'program.hex', run/'program.ir.json', **options)
    actual = run/'INICIO.X86'
    if actual.stat().st_size != len(packet) or actual.read_bytes() != packet:
        raise ValueError('PACKET-MISMATCH')
    lines = ['# Lectura del HEX comprobado', '',
             f'Perfil: x86-64 / {profile}. Comprobacion HOST; ejecucion QEMU documentada por separado.', '',
             f'Cuerpo: {report["BodyBytes"]} bytes. Paquete: {report["PacketBytes"]} bytes.',
             f'SHA-256 del paquete: `{report["PacketSHA256"]}`.', '']
    if budget := report.get('EntryBudget'):
        lines.extend([
            f'Presupuesto de entrada: paquete < {budget["LimitExclusive"]} bytes.',
            f'Cabecera: {budget["HeaderBytes"]} bytes. Margen utilizable: {budget["RemainingBytes"]} bytes.',
            f'Archivo HEX de texto: {(run/"program.hex").stat().st_size} bytes.',
            '',
        ])
    lines.extend(['| Linea | Offset cuerpo | Offset paquete | Clase | Bytes |',
                  '|---|---|---|---|---|'])
    body = packet[24:]
    for row in report['Mapping']:
        start, size = row['Offset'], row['Bytes']
        tokens = body[start:start+size]
        preview = tokens[:64].hex(' ').upper()
        if size > 64:
            preview += f' ... ({size-64} bytes omitidos)'
        lines.append(f'| {row["Line"]} | {start} | {start+24} | {row["Kind"]} | `{preview}` |')
    lines.extend(['', 'Cada offset se mide en bytes. La cabecera ocupa 24 bytes.',
                  'La comprobacion contrasta emision e IR; la semantica de la fuente depende del frontend.',
                  'La precision del HEX no configura el privilegio del procesador.', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    build = (ROOT/'build/CASM').resolve()
    if not run.is_relative_to(build) or not run.name.startswith('run-'):
        raise ValueError('Se requiere un run dentro de build/CASM')
    text = render(run)
    output = run/'HEX.md'
    output.write_text(text, encoding='ascii', newline='\n')
    print(output)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit(f'RED [HEX-REPORT] {error}') from error
