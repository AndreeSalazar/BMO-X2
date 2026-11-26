"""Decode the opt-in BMO-X2 GSP init failure snapshot exported over serial."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib


PAGE = 4096
TRACE_BYTES = 17 * PAGE
ROW_BYTES = 64
BEGIN = b'BMO_GSP_BEGIN=1 11000'
END = re.compile(rb'BMO_GSP_END=1 11000 ([0-9A-F]{8})')
ROW = re.compile(rb'GSPD=([0-9A-F]{5}):([0-9A-F]{128})')
SUMMARY = re.compile(rb'GSP_TRACE=(' + rb'[0-9A-F]{8} ' * 8 + rb'[0-9A-F]{16})')


def read_serial(stream):
    active = capture = summary = snapshot_summary = None
    for raw in stream:
        line = raw.rstrip(b'\r\n')
        if active is None and (match := SUMMARY.fullmatch(line)):
            summary = [int(word, 16) for word in match[1].split()]
        if line.startswith(b'BMO_GSP_BEGIN='):
            if line != BEGIN or active is not None:
                raise ValueError('Inicio de captura GSP invalido')
            active = bytearray()
            snapshot_summary = summary
        elif active is not None and line.startswith(b'BMO_GSP_END='):
            footer = END.fullmatch(line)
            if not footer or len(active) != TRACE_BYTES:
                raise ValueError('Captura GSP incompleta')
            if int(footer[1], 16) != zlib.crc32(active):
                raise ValueError('CRC32 de captura GSP incorrecto')
            capture, active = (bytes(active), snapshot_summary), None
        elif active is not None:
            row = ROW.fullmatch(line)
            if not row or int(row[1], 16) != len(active) or len(active) >= TRACE_BYTES:
                raise ValueError('Fila de captura GSP invalida o fuera de orden')
            active.extend(bytes.fromhex(row[2].decode('ascii')))
    if active is not None or capture is None:
        raise ValueError('Falta una captura GSP completa')
    return capture


def decode(trace, summary=None):
    if len(trace) != TRACE_BYTES:
        raise ValueError('La captura GSP debe tener 17 paginas')
    tx_head, tx_tail, event_bytes, producer_after = struct.unpack_from('<4I', trace, PAGE - 16)
    if event_bytes > PAGE - 16 or event_bytes % 16:
        raise ValueError('Longitud de eventos AMD-Vi invalida')
    producer, log_iova = struct.unpack_from('<QQ', trace, PAGE)
    log_key = 'logrm' if log_iova == 0x0A0A3000 else 'loginit'
    groups = Counter()
    for device, detail, low, high in struct.iter_unpack('<4I', trace[:event_bytes]):
        kind = detail >> 28
        if kind:
            groups[(device & 0xffff, kind, (detail >> 16) & 0xfff, detail & 0xffff, (high << 32) | low)] += 1

    events = []
    for (devid, kind, flags, context, address), count in groups.items():
        events.append(dict(requester=f'{devid >> 8:02x}:{(devid >> 3) & 31:02x}.{devid & 7}',
                           event_type=kind, event='IO_PAGE_FAULT' if kind == 2 else None,
                           flags=f'0x{flags:03X}', context_raw=f'0x{context:04X}',
                           address=f'0x{address:016X}', count=count))
    report = dict(schema=1, evidence='BMO-X2 GSP init failure snapshot', sha256=hashlib.sha256(trace).hexdigest(),
                  tx_head=tx_head, tx_tail=tx_tail, event_bytes=event_bytes, events=events)
    report[log_key] = dict(producer=f'0x{producer:016X}', producer_after_low=f'0x{producer_after:08X}',
                           self_iova=f'0x{log_iova:016X}', sha256=hashlib.sha256(trace[PAGE:]).hexdigest())
    if summary is not None:
        mailbox0, mailbox1, cpu, rx, before, tail, status, first, address = summary
        report.update(mailboxes=[f'0x{mailbox0:08X}', f'0x{mailbox1:08X}'],
                      cpuctl=f'0x{cpu:08X}', rx_head=rx, amdvi_tail_bytes=tail,
                      amdvi_status=f'0x{status:08X}', first_event_summary=f'0x{first:08X}',
                      first_event_address=f'0x{address:016X}')
        report[log_key].update(producer_before_low=f'0x{before:08X}',
                                 producer_changed_during_copy=(before != producer_after or
                                                               before != (producer & 0xffffffff)))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('serial', type=Path)
    parser.add_argument('--raw', type=Path, help='Write the validated 17-page capture to a binary file')
    args = parser.parse_args()
    if args.raw and args.raw.resolve() == args.serial.resolve():
        parser.error('El archivo bruto debe ser distinto del registro serie')
    try:
        with args.serial.open('rb') as stream:
            trace, summary = read_serial(stream)
        report = decode(trace, summary)
        if args.raw:
            args.raw.write_bytes(trace)
    except (OSError, ValueError) as error:
        parser.exit(1, f'GSP: {error}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
