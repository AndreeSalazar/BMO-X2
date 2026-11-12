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
HD_PROFILE = 'ring0-splash-hd-0.1'
ASSETS = Path(__file__).resolve().parents[1]/'kernel/boot/splash'


def read_rows(source, *, hd=False):
    cells = 64 if hd else 32
    require(len(source) <= (8192 if hd else 4096) and all(0 < value < 128 for value in source), 'SPLASH-SOURCE-SIZE')
    text = source.decode('ascii')
    token = rf'[A-Za-z_][A-Za-z_0-9]*|[(){{}};]|"[.#o]{{{cells}}}"'
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
    require(len(args) == cells and all(value.startswith('"') for value in args), 'SPLASH-SOURCE-ROWS')
    return [value[1:-1] for value in args], text.count('\n', 0, matches[6].start())+1, text.count('\n', 0, matches[-5].start())+1


def verify(source_path, hex_path, ir_path, *, hd=False):
    for path, limit in [(source_path, 8192 if hd else 4096), (hex_path, 4096 if hd else 2048), (ir_path, 4096)]:
        require(path.stat().st_size <= limit, 'SPLASH-INPUT-SIZE')
    source, hex_text, ir_bytes = (p.read_bytes() for p in (source_path, hex_path, ir_path))
    rows, line, halt = read_rows(source, hd=hd)
    ir = json.loads(ir_bytes, object_pairs_hook=no_duplicates)
    cells = 64 if hd else 32
    renderer_size, frame_offset, halt_offset, body_size = (231,172,216,1255) if hd else (228,169,213,484)
    profile = HD_PROFILE if hd else PROFILE
    expected = dict(Schema=6, Target='x86_64', ABI='ring0-splash', Profile=profile,
                    Entry='kernel_main', RequiredCPL=0, BodyBytes=body_size,
                    Logo=dict(Line=line, Offset=renderer_size, Width=cells, Height=cells, Scale=256//cells, Frames=3),
                    Terminal=dict(Line=halt, Offset=halt_offset))
    require(json.dumps(ir, sort_keys=True) == json.dumps(expected, sort_keys=True), 'SPLASH-IR')
    reference = bytes.fromhex(((ASSETS/'hd' if hd else ASSETS)/'expected-code.hex').read_text(encoding='ascii'))
    require(len(reference) == renderer_size, 'SPLASH-REFERENCE')
    mask = b''.join(sum(2**x for x, char in enumerate(row) if char == mark).to_bytes(cells//8,'little')
                    for row in rows for mark in '#o')
    tokens = hex_text.decode('ascii').split()
    require(len(tokens) == body_size and all(re.fullmatch('[0-9A-Fa-f]{2}', t) for t in tokens), 'SPLASH-HEX')
    body = bytes(int(t, 16) for t in tokens)
    require(body[:renderer_size] == reference, 'SPLASH-RENDERER')
    require(body[renderer_size:] == mask, 'SPLASH-MASK')
    packet = b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body
    report = dict(Schema=1, Verified=True, Target='x86_64', ABI='ring0-splash', Profile=profile,
                  BodyBytes=len(body), PacketBytes=len(packet),
                  Mapping=[dict(Line=halt if start == halt_offset else line, Offset=start, Bytes=end-start, Kind=kind)
                           for start, end, kind in [(0,24,'handoff-guard'),(24,77,'center-and-locate-mask'),
                                                   (77,101,'palette-and-pixel-order'),(101,frame_offset,'draw-256x256'),
                                                   (frame_offset,halt_offset,'frame-count-and-delay'),(halt_offset,halt_offset+3,'halt'),
                                                   (halt_offset+3,renderer_size,'eye-palette'),(renderer_size,body_size,'cat-masks')]])
    if hd:
        require(len(packet) <= 4096, 'SPLASH-BRIDGE-LIMIT')
        report['BridgePacketLimitBytes'] = 4096
    else:
        report['EntryBudget'] = entry_budget(len(body), len(packet))
    for key, data in [('Source',source),('Hex',hex_text),('IR',ir_bytes),('Packet',packet)]:
        report[key+'SHA256'] = hashlib.sha256(data).hexdigest()
    return packet, report


def check(run, *, hd=False):
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json', hd=hd)
    require((run/'source.casm').read_bytes() == ((ASSETS/'hd' if hd else ASSETS)/'main.casm').read_bytes(), 'SPLASH-CANONICAL-SOURCE')
    require((run/'INICIO.X86').read_bytes() == packet, 'SPLASH-PACKET')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','hex','ir'):
        p.add_argument(name, type=Path)
    p.add_argument('--packet', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    p.add_argument('--hd', action='store_true')
    args = p.parse_args()
    outputs = {args.packet.resolve(), args.report.resolve()}
    require(len(outputs) == 2 and not outputs.intersection(
            p.resolve() for p in (args.source,args.hex,args.ir,ASSETS/'expected-code.hex',ASSETS/'hd/expected-code.hex')), 'SPLASH-OUTPUT-ALIAS')
    packet, report = verify(args.source, args.hex, args.ir, hd=args.hd)
    args.packet.write_bytes(packet)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii',newline='\n')
    print(f'GREEN [SPLASH-VERIFY] {len(packet)} bytes packaged.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        raise SystemExit(f'RED [SPLASH-VERIFY] {error}') from error
