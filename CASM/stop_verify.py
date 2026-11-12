"""Independent closed source/IR/byte verifier for ring0-stop-0.1."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from entry_budget import entry_budget

PROFILE = 'ring0-stop-0.1'
CPU_PROFILE = 'ring0-cpu-0.1'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_lines(source, identify):
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
    prefix = ['void', 'kernel_main', '(', 'void', ')', '{']
    if identify:
        prefix += ['cpu_identify', '(', ')', ';']
    require([v for v, line in tokens] == prefix + ['cpu_halt', '(', ')', ';', '}'], 'STOP-SOURCE-GRAMMAR')
    return tokens[len(prefix)][1], tokens[6][1] if identify else None


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'STOP-IR-DUPLICATE')
        result[key] = value
    return result


def verify(source_path, hex_path, ir_path, *, identify=False):
    for path, limit in [(source_path, 65536), (hex_path, 128), (ir_path, 4096)]:
        require(path.stat().st_size <= limit, 'STOP-INPUT-SIZE')
    source = source_path.read_bytes()
    line, identification_line = source_lines(source, identify)
    ir = json.loads(ir_path.read_text(encoding='ascii'), object_pairs_hook=no_duplicates)
    expected = dict(Schema=3, Target='x86_64', ABI='ring0-stop', Profile=PROFILE,
                    Entry='kernel_main', RequiredCPL=0, Effects=['mask-interrupts', 'halt'],
                    Terminal=dict(Line=line, Offset=0), BodyBytes=4)
    vector = bytes([250, 244, 235, 253])
    mapping = [(line, 0, 1, 'cli'), (line, 1, 1, 'hlt'), (line, 2, 2, 'jmp-hlt')]
    if identify:
        expected = dict(Schema=4, Target='x86_64', ABI='ring0-cpu', Profile=CPU_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Identification=dict(Line=identification_line, Offset=1, Leaf=0),
                        Terminal=dict(Line=line, Offset=5), BodyBytes=8)
        vector = bytes.fromhex('FA 31 C0 0F A2 F4 EB FD')
        mapping = [(identification_line, 0, 1, 'cli'), (identification_line, 1, 2, 'xor-eax'),
                   (identification_line, 3, 2, 'cpuid'), (line, 5, 1, 'hlt'), (line, 6, 2, 'jmp-hlt')]
    require(json.dumps(ir, sort_keys=True) == json.dumps(expected, sort_keys=True), 'STOP-IR')
    tokens = hex_path.read_text(encoding='ascii').split()
    require(len(tokens) == len(vector) and all(re.fullmatch('[0-9A-Fa-f]{2}', t) for t in tokens), 'STOP-HEX')
    body = bytes(int(t, 16) for t in tokens)
    # Independent manual instruction vector: no import of compiler or profile table.
    require(body == vector, 'STOP-EMISSION')
    packet = b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body
    report = dict(Schema=1, Verified=True, Target='x86_64', ABI=expected['ABI'], Profile=expected['Profile'],
                  BodyBytes=len(body), PacketBytes=len(packet), Integers=[],
                  EntryBudget=entry_budget(len(body), len(packet)),
                  Mapping=[dict(Line=ln, Offset=o, Bytes=n, Kind=k) for ln, o, n, k in mapping],
                  Scope='Closed source grammar and exact emission; CPL0 required; QEMU evidence separate.')
    for key, data in [('Source', source), ('Hex', hex_path.read_bytes()),
                      ('IR', ir_path.read_bytes()), ('Packet', packet)]:
        report[key + 'SHA256'] = hashlib.sha256(data).hexdigest()
    return packet, report


def check(run, *, identify=False):
    root = Path(__file__).resolve().parents[1]
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json', identify=identify)
    source = root / ('kernel/arch/x86_64/cpu/identify.casm' if identify else 'kernel/boot/stop/main.casm')
    vector = source.with_suffix('.hex') if identify else source.with_name('expected.hex')
    require((run/'source.casm').read_bytes() == source.read_bytes(), 'STOP-CANONICAL-SOURCE')
    require(bytes.fromhex(vector.read_text()) == packet[24:], 'STOP-MANUAL-VECTOR')
    require((run/'INICIO.X86').read_bytes() == packet, 'STOP-PACKET')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'hex', 'ir']:
        p.add_argument(name, type=Path)
    p.add_argument('--packet', required=True, type=Path)
    p.add_argument('--report', required=True, type=Path)
    p.add_argument('--identify', action='store_true')
    args = p.parse_args()
    outputs = [args.packet.resolve(), args.report.resolve()]
    require(len(set(outputs)) == 2 and not set(outputs).intersection(
            path.resolve() for path in [args.source, args.hex, args.ir]), 'STOP-OUTPUT-ALIAS')
    packet, report = verify(args.source, args.hex, args.ir, identify=args.identify)
    args.packet.write_bytes(packet)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(f'GREEN [STOP-VERIFY] {report["BodyBytes"]} body bytes; {len(packet)} packet bytes independently checked.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        raise SystemExit(f'RED [STOP-VERIFY] {error}') from error
