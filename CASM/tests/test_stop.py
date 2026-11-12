"""Closed privileged profile: source boundary, manual vector and hostile IR/HEX."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'CASM'))
from stop_verify import verify
from verify import verify as legacy_verify


class Stop(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source, self.hex, self.ir = [self.path/name for name in ['source.casm', 'program.hex', 'program.ir.json']]
        self.source.write_bytes((ROOT/'kernel/boot/stop/main.casm').read_bytes())
        self.compiler = ROOT/'build/CASM/host/casmc.exe'

    def compile(self, profile=True):
        args = ['--profile', 'ring0-stop-0.1'] if profile else []
        return subprocess.run([str(self.compiler), *args, str(self.source), str(self.hex), str(self.ir)], capture_output=True)

    def test_source_line_comments_and_manual_vector(self):
        self.source.write_bytes(b'// cpu_halt();\nvoid/*split*/kernel_main(void) {\n/* more\n */ cpu_halt ( ) ; } // end')
        self.assertEqual(self.compile().returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir)
        self.assertEqual(packet[24:], bytes.fromhex((ROOT/'kernel/boot/stop/expected.hex').read_text()))
        self.assertEqual(len(packet), 28)
        self.assertEqual(report['EntryBudget'],
                         dict(HeaderBytes=24, LimitExclusive=512, RemainingBytes=483))
        self.assertEqual(report['Mapping'][0]['Line'], 4)
        with self.assertRaises(ValueError): legacy_verify(self.source, self.hex, self.ir)

    def test_closed_grammar_both_analyzers(self):
        original = self.source.read_bytes()
        self.assertEqual(self.compile().returncode, 0)
        bad = [original.replace(b'cpu_halt();', value) for value in
               [b'', b'return;', b'cpu_halt(1);', b'cpu_halt(); return;', b'cpu_halt(); cpu_halt();',
                b'metal_puts("x");', b'asm("hlt");', b'const u64 x=1; cpu_halt();']]
        bad += [original+b'void extra(void) {}', original.replace(b'kernel_main', b'metal_main'),
                original+b'/*', original+b'\x00', original+b'\xff', original.replace(b'void ', b'void\v', 1),
                b' '*65537]
        for source in bad:
            with self.subTest(source=source[:100]):
                self.source.write_bytes(source)
                self.assertNotEqual(self.compile().returncode, 0)
                with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.source.write_bytes(original)
        self.assertNotEqual(self.compile(False).returncode, 0)

    def test_cpu_profile_requires_exact_leaf_and_bytes(self):
        source = ROOT/'kernel/arch/x86_64/cpu/identify.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-cpu-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, identify=True)
        self.assertEqual(packet[24:], bytes.fromhex(source.with_suffix('.hex').read_text()))
        self.assertEqual(report['EntryBudget']['RemainingBytes'], 479)
        with self.assertRaises(ValueError):
            verify(self.source, self.hex, self.ir)
        original = self.ir.read_text()
        self.ir.write_text(original.replace('"Leaf":0', '"Leaf":1'))
        with self.assertRaisesRegex(ValueError, 'STOP-IR'):
            verify(self.source, self.hex, self.ir, identify=True)
        self.ir.write_text(original)
        self.hex.write_text('FA 31 C0 0F A3 F4 EB FD')
        with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
            verify(self.source, self.hex, self.ir, identify=True)

    def test_stack_profile_rejects_changed_stack_top_and_branch(self):
        source = ROOT/'kernel/boot/context/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-context-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, context=True)
        self.assertEqual(packet[24:], bytes.fromhex(source.with_name('expected.hex').read_text()))
        self.assertEqual(report['EntryBudget']['RemainingBytes'], 437)
        ir = self.ir.read_text()
        self.ir.write_text(ir.replace('"Top":81920', '"Top":131072'))
        with self.assertRaisesRegex(ValueError, 'STOP-IR'):
            verify(self.source, self.hex, self.ir, context=True)
        self.ir.write_text(ir)
        self.hex.write_text(self.hex.read_text().replace('75 24', '75 23'))
        with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
            verify(self.source, self.hex, self.ir, context=True)

    def test_fault_profile_checks_vector_limit_and_opcode(self):
        source = ROOT/'kernel/arch/x86_64/exceptions/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-fault-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source,self.hex,self.ir,fault=True)
        self.assertEqual(packet[24+122:24+124], bytes.fromhex('0F 0B'))
        self.assertEqual(len(packet), 162)
        self.assertEqual(report['EntryBudget']['RemainingBytes'],349)
        original = self.ir.read_text()
        for old, new in [('"Vector":6','"Vector":7'),('"IdtLimit":111','"IdtLimit":95')]:
            self.ir.write_text(original.replace(old,new))
            with self.assertRaisesRegex(ValueError,'STOP-IR'):
                verify(self.source,self.hex,self.ir,fault=True)
        self.ir.write_text(original)
        self.hex.write_text(self.hex.read_text().replace('0F 0B','90 90'))
        with self.assertRaisesRegex(ValueError,'STOP-EMISSION'):
            verify(self.source,self.hex,self.ir,fault=True)

    def test_memory_profile_checks_bound_and_emission(self):
        source = ROOT/'kernel/mm/physical/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-memory-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, memory=True)
        self.assertEqual(len(packet), 241)
        self.assertEqual(report['EntryBudget']['RemainingBytes'], 270)
        ir = json.loads(self.ir.read_text())
        for key in ('MapOffset', 'PageBytes', 'LimitExclusive'):
            mutated = copy.deepcopy(ir)
            mutated['Frame'][key] *= 2
            self.ir.write_text(json.dumps(mutated))
            with self.assertRaisesRegex(ValueError, 'STOP-IR'):
                verify(self.source, self.hex, self.ir, memory=True)
        self.ir.write_text(json.dumps(ir))
        vector = bytearray(packet[24:])
        vector[181] ^= 1
        self.hex.write_text(vector.hex(' '))
        with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
            verify(self.source, self.hex, self.ir, memory=True)

    def test_frame_cycle_rejects_weakened_scrub_and_capacity(self):
        source = ROOT/'kernel/mm/physical/lifecycle/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-frame-cycle-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, cycle=True)
        self.assertEqual(len(packet), 498)
        self.assertEqual(report['EntryBudget']['RemainingBytes'], 13)
        ir = json.loads(self.ir.read_text())
        for key, value in [('Capacity', 2), ('ScrubOnRelease', False)]:
            modified = copy.deepcopy(ir)
            modified['Pool'][key] = value
            self.ir.write_text(json.dumps(modified))
            with self.assertRaisesRegex(ValueError, 'STOP-IR'):
                verify(self.source, self.hex, self.ir, cycle=True)
        self.ir.write_text(json.dumps(ir))
        vector = bytearray(packet[24:])
        scrub = vector.index(bytes.fromhex('F3 48 AB'), 442)
        vector[scrub] = 0x90
        self.hex.write_text(vector.hex(' '))
        with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
            verify(self.source, self.hex, self.ir, cycle=True)
        self.source.write_bytes(self.source.read_bytes().replace(b'boot_frame_cycle', b'boot_memory'))
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)

    def test_paging_rejects_changed_alias_permissions_and_cr3(self):
        source = ROOT/'kernel/mm/virtual/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-paging-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, paging=True)
        self.assertEqual(len(packet), 497)
        self.assertEqual(report['EntryBudget']['RemainingBytes'], 14)
        ir = json.loads(self.ir.read_text())
        for key, value in [('AliasUserReadOnlyNX', False), ('TableFrames', 4), ('Alias', 0)]:
            changed = copy.deepcopy(ir)
            changed['Paging'][key] = value
            self.ir.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'STOP-IR'):
                verify(self.source, self.hex, self.ir, paging=True)
        self.ir.write_text(json.dumps(ir))
        body = packet[24:]
        for opcode, index, value in [('49 8D 83 05 50 00 00', 3, 7), ('41 0F 22 DB', 3, 0xd8)]:
            changed = bytearray(body)
            changed[body.index(bytes.fromhex(opcode)) + index] = value
            self.hex.write_text(changed.hex(' '))
            with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
                verify(self.source, self.hex, self.ir, paging=True)

    def test_user_fault_requires_iret_and_page_teardown(self):
        source = ROOT/'kernel/mm/user/main.casm'
        self.source.write_bytes(source.read_bytes())
        cmd = [str(self.compiler), '--profile', 'ring0-user-fault-0.1',
               str(self.source), str(self.hex), str(self.ir)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        packet, report = verify(self.source, self.hex, self.ir, user_fault=True)
        self.assertEqual(len(packet), 740)
        self.assertEqual(report['BridgePacketLimitBytes'], 4096)
        ir = json.loads(self.ir.read_text())
        ir['Process']['ErrorCode'] = 4
        self.ir.write_text(json.dumps(ir))
        with self.assertRaisesRegex(ValueError, 'STOP-IR'):
            verify(self.source, self.hex, self.ir, user_fault=True)
        ir['Process']['ErrorCode'] = 5
        self.ir.write_text(json.dumps(ir))
        body = packet[24:]
        for opcode in ('48 CF', '0F 01 39', 'F3 48 AB'):
            start = 605 if opcode == 'F3 48 AB' else 0
            changed = bytearray(body)
            changed[body.index(bytes.fromhex(opcode), start)] = 0x90
            self.hex.write_text(changed.hex(' '))
            with self.assertRaisesRegex(ValueError, 'STOP-EMISSION'):
                verify(self.source, self.hex, self.ir, user_fault=True)

    def test_all_byte_bits_and_ir_contract_reject(self):
        self.assertEqual(self.compile().returncode, 0)
        vector = bytes.fromhex(self.hex.read_text())
        for index in range(4):
            for bit in range(8):
                mutated = bytearray(vector); mutated[index] ^= 1 << bit
                self.hex.write_text(mutated.hex(' '))
                with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.hex.write_text(vector.hex(' '))
        original = json.loads(self.ir.read_text())
        for key in original:
            mutated = copy.deepcopy(original); del mutated[key]
            self.ir.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        for key, value in [('RequiredCPL', False), ('Schema', 2), ('ABI', 'metal64'),
                           ('Effects', ['halt']), ('Terminal', {'Line': 2, 'Offset': 1}),
                           ('Terminal', {'Line': 1, 'Offset': 0}), ('BodyBytes', 5)]:
            mutated = copy.deepcopy(original); mutated[key] = value
            self.ir.write_text(json.dumps(mutated))
            with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)
        self.ir.write_text(json.dumps(original)[:-1]+',"Schema":3}')
        with self.assertRaises(ValueError): verify(self.source, self.hex, self.ir)

    def test_cli_rejection_publishes_nothing(self):
        self.assertEqual(self.compile().returncode, 0)
        self.hex.write_text('FA F4 EB FC')
        packet, report = self.path/'INICIO.X86', self.path/'verified.json'
        result = subprocess.run([sys.executable, '-B', str(ROOT/'CASM/stop_verify.py'),
                                 str(self.source), str(self.hex), str(self.ir), '--packet', str(packet),
                                 '--report', str(report)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(packet.exists()); self.assertFalse(report.exists())


if __name__ == '__main__': unittest.main()
