"""Genesis G0: manual byte vector, independent verification and strict size budget."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'CASM'))
from verify import verify


def budget(body_bytes, packet_bytes):
    if not 0 < body_bytes < 512 or not 24 < packet_bytes < 512 or packet_bytes != body_bytes + 24:
        raise ValueError('GENESIS-BUDGET')


def check(run):
    source = ROOT/'kernel/boot/genesis/main.casm'
    if (run/'source.casm').read_bytes() != source.read_bytes():
        raise ValueError('GENESIS-SOURCE')
    expected = bytes.fromhex((ROOT/'kernel/boot/genesis/expected.hex').read_text())
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json')
    if packet[24:] != expected:
        raise ValueError('GENESIS-VECTOR')
    budget(len(expected), len(packet))
    if (run/'INICIO.X86').read_bytes() != packet:
        raise ValueError('GENESIS-PACKET')
    return dict(schema=1, milestone='Genesis G0', evidence='HOST', profile='metal64-0.2',
                body_bytes=len(expected), code_bytes=12, data_bytes=len(expected)-12, packet_bytes=len(packet),
                hex_file_bytes=(run/'program.hex').stat().st_size, budget_exclusive=512,
                packet_sha256=hashlib.sha256(packet).hexdigest(), source_sha256=report['SourceSHA256'],
                loader_included=False, executed=False, autonomous_kernel=False,
                result='manual vector, verifier and packet agree')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('run', type=Path)
    args = p.parse_args()
    try:
        run = args.run.resolve()
        if not run.is_relative_to((ROOT/'build/CASM').resolve()) or not run.name.startswith('run-'):
            raise ValueError('GENESIS-RUN')
        result = check(run)
        (run/'genesis.json').write_text(json.dumps(result, indent=2)+'\n',encoding='ascii',newline='\n')
        print(json.dumps(result, indent=2))
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise SystemExit(f'RED [GENESIS] {error}') from error
