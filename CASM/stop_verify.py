"""Independent closed source/IR/byte verifier for ring0-stop-0.1."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from entry_budget import entry_budget

PROFILE = 'ring0-stop-0.1'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_line(source):
    require(len(source) <= 65536 and all(0 < c < 128 for c in source), 'STOP-SOURCE-ASCII-SIZE')
    text = source.decode('ascii')
    tokens = []
    position = 0
    pattern = re.compile(r'[ \t\r\n]+|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_][A-Za-z_0-9]*|[(){};]')
    for match in pattern.finditer(text):
        require(match.start() == position, 'STOP-SOURCE-TOKEN')
        position = match.end()
        value = match.group()
        if value[0] in ' \t\r\n' or value.startswith('//') or value.startswith('/*'):
            continue
        tokens.append((value, text.count('\n', 0, match.start()) + 1))
    require(position == len(text), 'STOP-SOURCE-TOKEN')
    require([v for v, line in tokens] == ['void', 'kernel_main', '(', 'void', ')', '{',
            'cpu_halt', '(', ')', ';', '}'], 'STOP-SOURCE-GRAMMAR')
    return tokens[6][1]


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'STOP-IR-DUPLICATE')
        result[key] = value
    return result


def verify(source_path, hex_path, ir_path):
    for path, limit in [(source_path, 65536), (hex_path, 128), (ir_path, 4096)]:
        require(path.stat().st_size <= limit, 'STOP-INPUT-SIZE')
    source = source_path.read_bytes()
    line = source_line(source)
    ir = json.loads(ir_path.read_text(encoding='ascii'), object_pairs_hook=no_duplicates)
    expected = dict(Schema=3, Target='x86_64', ABI='ring0-stop', Profile=PROFILE,
                    Entry='kernel_main', RequiredCPL=0, Effects=['mask-interrupts', 'halt'],
                    Terminal=dict(Line=line, Offset=0), BodyBytes=4)
    require(json.dumps(ir, sort_keys=True) == json.dumps(expected, sort_keys=True), 'STOP-IR')
    tokens = hex_path.read_text(encoding='ascii').split()
    require(len(tokens) == 4 and all(re.fullmatch('[0-9A-Fa-f]{2}', t) for t in tokens), 'STOP-HEX')
    body = bytes(int(t, 16) for t in tokens)
    # Independent manual instruction vector: no import of compiler or profile table.
    require(body == bytes([250, 244, 235, 253]), 'STOP-EMISSION')
    packet = b'FAGRAW64' + struct.pack('<IIII', 4, 0, sum(body), 0) + body
    report = dict(Schema=1, Verified=True, Target='x86_64', ABI='ring0-stop', Profile=PROFILE,
                  BodyBytes=len(body), PacketBytes=len(packet), Integers=[],
                  EntryBudget=entry_budget(len(body), len(packet)),
                  Mapping=[dict(Line=line, Offset=o, Bytes=n, Kind=k) for o, n, k in
                           [(0, 1, 'cli'), (1, 1, 'hlt'), (2, 2, 'jmp-hlt')]],
                  Scope='Closed source grammar and exact emission; CPL0 required; QEMU evidence separate.')
    for key, data in [('Source', source), ('Hex', hex_path.read_bytes()),
                      ('IR', ir_path.read_bytes()), ('Packet', packet)]:
        report[key + 'SHA256'] = hashlib.sha256(data).hexdigest()
    return packet, report


def check(run):
    root = Path(__file__).resolve().parents[1]
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json')
    require((run/'source.casm').read_bytes() == (root/'kernel/boot/stop/main.casm').read_bytes(), 'STOP-CANONICAL-SOURCE')
    require(bytes.fromhex((root/'kernel/boot/stop/expected.hex').read_text()) == packet[24:], 'STOP-MANUAL-VECTOR')
    require((run/'INICIO.X86').read_bytes() == packet, 'STOP-PACKET')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'hex', 'ir']:
        p.add_argument(name, type=Path)
    p.add_argument('--packet', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    outputs = [args.packet.resolve(), args.report.resolve()]
    require(len(set(outputs)) == 2 and not set(outputs).intersection(
            path.resolve() for path in [args.source, args.hex, args.ir]), 'STOP-OUTPUT-ALIAS')
    packet, report = verify(args.source, args.hex, args.ir)
    args.packet.write_bytes(packet)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print('GREEN [STOP-VERIFY] 4 body bytes; 28 packet bytes independently checked.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        raise SystemExit(f'RED [STOP-VERIFY] {error}') from error
