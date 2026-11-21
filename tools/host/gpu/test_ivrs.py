"""Checks HOST sizing against the captured BMO-X2 IVRS and the QEMU table."""

import json
from pathlib import Path
import unittest

from tools.host.gpu import ivrs


ROOT = Path(__file__).resolve().parents[3]


class DeviceTableSizingTests(unittest.TestCase):
    def test_board_ivrs_requires_full_16_bit_device_table(self):
        capture = json.loads((ROOT / 'Reports/nvidia-gsp-host-20261120.json').read_text())
        data = bytes.fromhex(capture['ivrs_table_hex'])
        report = ivrs.inspect(data, [(0, 0x2900), (0, 0x2901)])

        self.assertEqual(report['table_sha256'], capture['ivrs']['table_sha256'])
        gpu_scope, = report['requesters']['0000:29:00.0']
        self.assertEqual(gpu_scope['range_last'], '0000:ff:1f.6')
        requirement, = report['device_table_requirements']
        self.assertEqual(requirement['scope_first'], '0000:00:01.0')
        self.assertEqual(requirement['scope_last'], '0000:ff:1f.7')
        self.assertEqual(requirement['scope_ranges'], [
            {'first': '0000:00:01.0', 'last': '0000:ff:1f.6', 'alias': None},
            {'first': '0000:ff:00.0', 'last': '0000:ff:1f.7', 'alias': '00a5'},
        ])
        self.assertEqual(requirement['highest_device_id'], 'ffff')
        self.assertEqual(requirement['minimum_entries'], 0x10000)
        self.assertEqual(requirement['minimum_4k_pages'], 512)
        self.assertEqual(requirement['minimum_aligned_bytes'], 2 * 1024 * 1024)

    def test_qemu_routed_lab_geometry_is_96_pages(self):
        units = {
            (0, 0x0002): (0x11, 0, 0x40, 0xFED80000, [(0x0008, 0x2fff, None)]),
        }
        requirement, = ivrs.device_table_requirements(units)

        self.assertEqual(requirement['minimum_entries'], 0x3000)
        self.assertEqual(requirement['minimum_4k_pages'], 96)
        self.assertEqual(requirement['minimum_aligned_bytes'], 96 * 4096)


if __name__ == '__main__':
    unittest.main()
