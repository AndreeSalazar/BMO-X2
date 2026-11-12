"""Validate source rows, exact x86-64 renderer and packed masks before packaging."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from entry_budget import entry_budget
from stop_verify import no_duplicates, require

PROFILE = 'ring0-splash-0.1'
ASSETS = Path(__file__).resolve().parents[1]/'kernel/boot/splash'


def read_rows(source):
    require(len(source) <= 4096 and all(0 < value < 128 for value in source), 'SPLASH-SOURCE-SIZE')
    text = source.decode('ascii')
    token = r'[A-Za-z_][A-Za-z_0-9]*|[(){};]|"[.#o]{32}"'
    matches = list(re.finditer(token, text))
    position = 0
    for match in matches:
        require(not text[position:match.start()].strip(' \t\r\n'), 'SPLASH-SOURCE-TOKEN')
        position = match.end()
    require(not text[position:].strip(' \t\r\n'), 'SPLASH-SOURCE-TOKEN')
    values = [match.group() for match in matches]
    require(values[:8] == ['void','kernel_main','(','void',')','{','boot_cat','(']
            and values[-7:] == [')',';','cpu_halt','(',')',';','}'], 'SPLASH-SOURCE-GRAMMAR')
    args = values[8:-7]
    require(len(args) == 32 and all(value.startswith('"') for value in args), 'SPLASH-SOURCE-ROWS')
    return [value[1:-1] for value in args], text.count('\n', 0, matches[6].start())+1, text.count('\n', 0, matches[-5].start())+1


def verify(source_path, hex_path, ir_path):
    for path, limit in [(source_path, 4096), (hex_path, 2048), (ir_path, 4096)]:
        require(path.stat().st_size <= limit, 'SPLASH-INPUT-SIZE')
    source, hex_text, ir_bytes = (p.read_bytes() for p in (source_path, hex_path, ir_path))
    rows, line, halt = read_rows(source)
    ir = json.loads(ir_bytes, object_pairs_hook=no_duplicates)
    expected = dict(Schema=6, Target='x86_64', ABI='ring0-splash', Profile=PROFILE,
                    Entry='kernel_main', RequiredCPL=0, BodyBytes=484,
                    Logo=dict(Line=line, Offset=228, Width=32, Height=32, Scale=8, Frames=3),
                    Terminal=dict(Line=halt, Offset=213))
    require(json.dumps(ir, sort_keys=True) == json.dumps(expected, sort_keys=True), 'SPLASH-IR')
    reference = bytes.fromhex((ASSETS/'expected-code.hex').read_text(encoding='ascii'))
    require(len(reference) == 228, 'SPLASH-REFERENCE')
    mask = b''.join(struct.pack('<I', sum(2**x for x, char in enumerate(row) if char == mark))
                    for row in rows for mark in '#o')
    tokens = hex_text.decode('ascii').split()
    require(len(tokens) == 484 and all(re.fullmatch('[0-9A-Fa-f]{2}', t) for t in tokens), 'SPLASH-HEX')
    body = bytes(int(t, 16) for t in tokens)
    require(body[:228] == reference, 'SPLASH-RENDERER')
    require(body[228:] == mask, 'SPLASH-MASK')
    packet = b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body
    report = dict(Schema=1, Verified=True, Target='x86_64', ABI='ring0-splash', Profile=PROFILE,
                  BodyBytes=len(body), PacketBytes=len(packet), EntryBudget=entry_budget(len(body), len(packet)),
                  Mapping=[dict(Line=halt if start == 213 else line, Offset=start, Bytes=end-start, Kind=kind)
                           for start, end, kind in [(0,24,'handoff-guard'),(24,77,'center-and-locate-mask'),
                                                   (77,101,'palette-and-pixel-order'),(101,169,'draw-256x256'),
                                                   (169,213,'frame-count-and-delay'),(213,216,'halt'),
                                                   (216,228,'eye-palette'),(228,484,'cat-masks')]])
    for key, data in [('Source',source),('Hex',hex_text),('IR',ir_bytes),('Packet',packet)]:
        report[key+'SHA256'] = hashlib.sha256(data).hexdigest()
    return packet, report


def check(run):
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json')
    require((run/'source.casm').read_bytes() == (ASSETS/'main.casm').read_bytes(), 'SPLASH-CANONICAL-SOURCE')
    require((run/'INICIO.X86').read_bytes() == packet, 'SPLASH-PACKET')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','hex','ir'):
        p.add_argument(name, type=Path)
    p.add_argument('--packet', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    outputs = {args.packet.resolve(), args.report.resolve()}
    require(len(outputs) == 2 and not outputs.intersection(
            p.resolve() for p in (args.source,args.hex,args.ir,ASSETS/'expected-code.hex')), 'SPLASH-OUTPUT-ALIAS')
    packet, report = verify(args.source, args.hex, args.ir)
    args.packet.write_bytes(packet)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii',newline='\n')
    print(f'GREEN [SPLASH-VERIFY] {len(packet)} bytes packaged.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        raise SystemExit(f'RED [SPLASH-VERIFY] {error}') from error
