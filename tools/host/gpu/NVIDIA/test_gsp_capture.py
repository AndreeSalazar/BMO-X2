"""Verify the serial export with the same C++ encoder as the optional guest."""
import io
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
import zlib

from .gsp_capture import (compare_logrm, decode, decode_event_pages, decode_packed_tail,
                          read_openrm_logrm, read_screen, read_serial)


ROOT = Path(__file__).resolve().parents[4]
LLVM = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LLVM/bin'
SOURCE = r'''
#include "userspace/drivers/GPU/NVIDIA/gsp_capture.hpp"
#include <cstdio>

int main() {
    BmoNvidia::InitReceipt init{};
    if (!BmoNvidia::read_init_receipt([](unsigned selector) -> uint64_t {
        switch (selector - 0x2400) {
        case 0: return 544;
        case 11: return 0x000000a100000003;
        case 24: return 0x120001031;
        case 25: return 0x870000;
        case 33: return 0x0043dc1300000052;
        case 42: return 0x120001000;
        case 43: return 0x402;
        case 67: return 0x120001033;
        case 68: return 1;
        default: return 0;
        }
    }, init)) return 1;
    std::printf("INIT TX / REV %08X LINK %08X PCIE %08X MEM %08X CL %08X CRC %08X\n",
                init.revision, init.link, init.pcie, init.console, init.cl, init.crc);
    std::puts("GSP_TRACE=000000CB 00000000 000000A0 00000000 00000049 00000020 0000001A 20002900 0000000000000000");
    BmoNvidia::export_gsp_trace([](unsigned selector) -> uint64_t {
        switch (selector - BmoNvidia::trace_selector) {
        case 0:
        case 2: return 0x2000000500002900;
        case 510: return 0x0000000000000001;
        case 511: return 0x0000004900000020;
        case 512: return 0x49;
        case 513: return 0x0a083000;
        default: return 0;
        }
    }, [](const char* text) { std::fputs(text, stdout); });
}
'''


class GspScreenCapture(unittest.TestCase):
    def test_event_pages_require_all_rows_and_group_by_phase(self):
        timeline = 'AMD-Vi colas / BOOT 000 SEC2 000 TX 050 RX 0A0\n'
        rows = [f'EV{i:03d} 00002900 20000005 00000000 {i // 5:08X}' for i in range(10)]
        report = decode_event_pages(timeline + '\n'.join(rows))
        phases = report['phases']
        self.assertEqual([phase['records'] for phase in phases], [0, 0, 5, 5])
        self.assertEqual(phases[2]['events'][0]['requester'], '29:00.0')
        self.assertEqual(phases[2]['events'][0]['address'], '0x0000000000000000')
        self.assertEqual(phases[3]['events'][0]['address'], '0x0000000100000000')
        with self.assertRaisesRegex(ValueError, 'Falta EV009'):
            decode_event_pages(timeline + '\n'.join(rows[:-1]))
        with self.assertRaisesRegex(ValueError, 'vuelta al inicio'):
            decode_event_pages(timeline.replace('RX 0A0', 'RX 030') + '\n'.join(rows))

    def test_compare_openrm_ring_tail_with_native_rejection(self):
        log = (
            'BMO_GSP_LOGRM_BEGIN=0000000000000002 0000000000000002\n'
            'BMO_GSP_LOGRM_WORD=0000000000000000 0302000000001234\n'
            'BMO_GSP_LOGRM_WORD=0000000000000001 0000000000000099\n'
            'BMO_GSP_LOGRM_END=2\n'
        )
        reference = decode_packed_tail(*read_openrm_logrm(log))
        native = decode_packed_tail('LOGRM', 4, 4,
                                    [0x0302000000001234, 0x88, 0x0302000000005678, 0x99])
        compared = compare_logrm(native, reference)
        self.assertEqual(compared['common_offsets'], ['0x000000001234'])
        self.assertEqual(compared['native_after_match'][0]['metadata_offset'], '0x000000005678')
        self.assertEqual(compared['openrm_after_match'], [])
        with self.assertRaisesRegex(ValueError, 'cambio'):
            read_openrm_logrm(log.replace(' 0000000000000002\n', ' 0000000000000003\n'))
        with self.assertRaisesRegex(ValueError, 'fuera de orden'):
            read_openrm_logrm(log.replace('WORD=0000000000000001', 'WORD=0000000000000002'))

    def test_decode_last_two_records(self):
        screen = (
            'LOGRM / ultimas palabras / 1 de 1\n'
            'Productor 0000000000000005 / despues 00000005\n'
            '00000000 0302000000001234 0000000000000099\n'
            '00000002 0000000000000040 0303000000005678\n'
            '00000004 0000000000000100\n'
        )
        report = decode_packed_tail(*read_screen(screen))
        self.assertEqual(report['undecoded_prefix_words'], 0)
        self.assertTrue(report['producer_matches_after'])
        records = report['candidate_records_newest_first']
        self.assertEqual([record['index'] for record in records], [2, 0])
        self.assertEqual(records[0]['arguments'], ['0x0000000000000040'])
        self.assertEqual(records[0]['metadata_offset'], '0x000000005678')
        with self.assertRaises(ValueError):
            read_screen(screen.replace('00000004 ', '00000005 '))
        with self.assertRaises(ValueError):
            read_screen(screen.rsplit('00000004 ', 1)[0])


class GspSerialCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as work:
            root = Path(work)
            source, exe = root / 'capture.cpp', root / 'capture.exe'
            source.write_text(SOURCE, encoding='ascii')
            subprocess.run([LLVM / 'clang++.exe', '-std=c++17', '-I', ROOT, source, '-o', exe], check=True)
            cls.serial = subprocess.check_output([exe])

    def test_snapshot_event_and_progress(self):
        report = decode(*read_serial(io.BytesIO(self.serial)))
        self.assertEqual((report['tx_head'], report['tx_tail'], report['rx_head']), (1, 0, 0))
        self.assertEqual(report['mailboxes'], ['0x000000CB', '0x00000000'])
        self.assertEqual(report['events'], [dict(requester='29:00.0', event_type=2, event='IO_PAGE_FAULT',
                                                flags='0x000', context_raw='0x0005',
                                                address='0x0000000000000000', count=2)])
        self.assertEqual(report['loginit']['self_iova'], '0x000000000A083000')
        self.assertFalse(report['loginit']['producer_changed_during_copy'])

    def test_init_receipt_matches_crc_over_exact_frame_bytes(self):
        frame = bytearray(544)
        for index, value in ((10, 0x000000a100000003), (23, 0x120001031),
                             (24, 0x870000), (32, 0x0043dc1300000052),
                             (41, 0x120001000), (42, 0x402), (66, 0x120001033), (67, 1)):
            struct.pack_into('<Q', frame, index * 8, value)
        expected = f'INIT TX / REV 000000A1 LINK 0043DC13 PCIE 00000402 MEM 00870000 CL 00000001 CRC {zlib.crc32(frame):08X}'
        self.assertEqual(self.serial.splitlines()[0], expected.encode('ascii'))

    def test_missing_row_and_truncation_are_rejected(self):
        for broken in (self.serial.replace(b'GSPD=00000:', b'GSPD=00040:', 1), self.serial[:-50]):
            with self.assertRaises(ValueError):
                read_serial(io.BytesIO(broken))

    def test_rm_log_is_reported_under_its_own_name(self):
        trace, summary = read_serial(io.BytesIO(self.serial))
        trace = bytearray(trace)
        struct.pack_into('<Q', trace, 4096+8, 0x0A0A3000)
        report = decode(trace, summary)
        self.assertEqual(report['logrm']['self_iova'], '0x000000000A0A3000')
        self.assertNotIn('loginit', report)

    def test_corruption_is_rejected_even_with_valid_hex(self):
        broken = self.serial.replace(b'GSPD=00000:00', b'GSPD=00000:01', 1)
        self.assertNotEqual(broken, self.serial)
        with self.assertRaisesRegex(ValueError, 'CRC32'):
            read_serial(io.BytesIO(broken))
