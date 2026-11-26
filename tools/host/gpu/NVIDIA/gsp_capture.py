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
SCREEN_HEADER = re.compile(r'(LOGRM|LOGINIT) / ultimas palabras / (\d+) de (\d+)')
SCREEN_PUT = re.compile(r'Productor ([0-9A-F]{16}) / despues ([0-9A-F]{8})')
SCREEN_ROW = re.compile(r'([0-9A-F]{8}) ([0-9A-F]{16})(?: ([0-9A-F]{16}))?')
LOG_WORDS = 65536 // 8 - 1
SCREEN_WORDS = 20


def read_screen(text):
    """Read one or more transcribed screen pages from a single snapshot."""
    identity = None
    pages = {}
    page = None
    for line in text.splitlines():
        if match := SCREEN_HEADER.fullmatch(line.strip()):
            log, number, count = match.groups()
            page = int(number)
            if page in pages or not 1 <= page <= int(count):
                raise ValueError('Pagina GSP invalida o duplicada')
            pages[page] = []
            producer = None
        elif page is not None and (match := SCREEN_PUT.fullmatch(line.strip())):
            put, after = (int(value, 16) for value in match.groups())
            observed = (log, put, after)
            maximum = min(put, LOG_WORDS)
            if identity not in (None, observed) or int(count) != (maximum + SCREEN_WORDS - 1) // SCREEN_WORDS:
                raise ValueError('Las paginas no corresponden a la misma captura GSP')
            identity = observed
            producer = put
        elif page is not None and (match := SCREEN_ROW.fullmatch(line.strip())):
            if producer is None:
                raise ValueError('Falta el productor de la pagina GSP')
            cursor, first, second = match.groups()
            end = producer - (page - 1) * SCREEN_WORDS
            start = max(producer - min(producer, LOG_WORDS), end - SCREEN_WORDS)
            words = pages[page]
            row = [int(word, 16) for word in (first, second) if word is not None]
            if int(cursor, 16) != (start + len(words)) & 0xffffffff or len(words) + len(row) > end - start:
                raise ValueError('Fila GSP fuera de orden o de rango')
            words.extend(row)
    if identity is None or not pages or sorted(pages) != list(range(1, len(pages) + 1)):
        raise ValueError('Se requieren paginas GSP consecutivas desde la primera')
    log, put, after = identity
    expected = min(put, LOG_WORDS)
    for page, words in pages.items():
        if len(words) != min(SCREEN_WORDS, expected - (page - 1) * SCREEN_WORDS):
            raise ValueError('Pagina GSP incompleta')
    return log, put, after, [word for page in sorted(pages, reverse=True) for word in pages[page]]


def decode_packed_tail(log, put, after, words):
    records = []
    cursor = len(words)
    # LibOS v2 stores arguments, then packed metadata, then a timestamp.
    while cursor >= 2:
        metadata, timestamp = words[cursor-2:cursor]
        task, size = metadata >> 56, (metadata >> 48) & 0xff
        if not 1 <= task <= 9 or not 2 <= size <= min(22, cursor):
            break
        records.append(dict(index=put-len(words)+cursor-size, task=task,
                            metadata_offset=f'0x{metadata & ((1 << 48) - 1):012X}',
                            timestamp=f'0x{timestamp:016X}',
                            arguments=[f'0x{arg:016X}' for arg in words[cursor-size:cursor-2]]))
        cursor -= size
    return dict(log=log, producer=put, producer_matches_after=(put & 0xffffffff) == after,
                words=words, candidate_records_newest_first=records, undecoded_prefix_words=cursor)


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
    parser.add_argument('--screen', action='store_true', help='Read the transcribed GSP tail panel')
    args = parser.parse_args()
    if args.screen and args.raw:
        parser.error('--screen no contiene las 17 paginas requeridas por --raw')
    if args.raw and args.raw.resolve() == args.serial.resolve():
        parser.error('El archivo bruto debe ser distinto del registro serie')
    try:
        if args.screen:
            report = decode_packed_tail(*read_screen(args.serial.read_text(encoding='utf-8-sig')))
        else:
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
