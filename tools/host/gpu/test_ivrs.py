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

    def test_physical_census_is_scope_joined_but_never_authorizes_translation(self):
        capture = json.loads((ROOT / 'Reports/nvidia-gsp-host-20261120.json').read_text())
        census = json.loads((ROOT / 'Reports/dma-pci-census-metal-20261120.json').read_text())
        data = bytes.fromhex(capture['ivrs_table_hex'])
        requested = [ivrs.bdf_arg(bdf) for bdf in census['ivrs_requesters']]
        report = ivrs.inspect(data, requested)

        audit = ivrs.reconcile_census(report, census)
        self.assertEqual(audit['observed_requesters'], 17)
        self.assertEqual(audit['bus_master_enabled'], 15)
        self.assertEqual(audit['scope_covered'], 17)
        self.assertEqual(audit['uncovered_requesters'], [])
        self.assertTrue(audit['all_observed_requesters_in_ivrs_scope'])
        self.assertTrue(audit['all_observed_requesters_unambiguous'])
        self.assertFalse(audit['all_domains_verified'])
        self.assertFalse(audit['physical_translation_permitted'])
        rtx, = [row for row in audit['requesters'] if row['bdf'] == '0000:29:00.0']
        self.assertFalse(rtx['bus_master_enabled'])
        self.assertEqual(rtx['vendor_device'], '10de:2504')
        self.assertEqual(rtx['device_evidence'], 'Reports/nvidia-pci-metal-20261120.json')
        self.assertFalse(rtx['domain_assignment_verified'])

    def test_uncovered_active_requester_keeps_translation_blocked(self):
        capture = json.loads((ROOT / 'Reports/nvidia-gsp-host-20261120.json').read_text())
        census = json.loads((ROOT / 'Reports/dma-pci-census-metal-20261120.json').read_text())
        data = bytes.fromhex(capture['ivrs_table_hex'])
        unknown = '0001:00:00.0'
        census['ivrs_requesters'].append(unknown)
        census['bus_master_enabled'].append({
            'bdf': unknown,
            'id': '1234:5678',
            'pci_class': '010802',
            'pci_command': '0007',
        })
        requested = [ivrs.bdf_arg(bdf) for bdf in census['ivrs_requesters']]
        report = ivrs.inspect(data, requested)

        audit = ivrs.reconcile_census(report, census)
        self.assertEqual(audit['uncovered_requesters'], [unknown])
        self.assertFalse(audit['all_observed_requesters_in_ivrs_scope'])
        self.assertFalse(audit['physical_translation_permitted'])

    def test_active_census_rejects_a_cleared_bus_master_bit(self):
        capture = json.loads((ROOT / 'Reports/nvidia-gsp-host-20261120.json').read_text())
        census = json.loads((ROOT / 'Reports/dma-pci-census-metal-20261120.json').read_text())
        data = bytes.fromhex(capture['ivrs_table_hex'])
        requested = [ivrs.bdf_arg(bdf) for bdf in census['ivrs_requesters']]
        report = ivrs.inspect(data, requested)
        census['bus_master_enabled'][0]['pci_command'] = '0003'

        with self.assertRaisesRegex(ValueError, 'no tiene Bus Master'):
            ivrs.reconcile_census(report, census)

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
