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
CONTEXT_PROFILE = 'ring0-context-0.1'
FAULT_PROFILE = 'ring0-fault-0.1'
FAULT_ASSETS = Path(__file__).resolve().parents[1]/'kernel/arch/x86_64/exceptions'
MEMORY_PROFILE = 'ring0-memory-0.1'
MEMORY_ASSETS = Path(__file__).resolve().parents[1]/'kernel/mm/physical'
CYCLE_PROFILE = 'ring0-frame-cycle-0.1'
CYCLE_ASSETS = MEMORY_ASSETS/'lifecycle'
PAGING_PROFILE = 'ring0-paging-0.1'
PAGING_ASSETS = MEMORY_ASSETS.parent/'virtual'
USER_FAULT_PROFILE = 'ring0-user-fault-0.1'
USER_FAULT_ASSETS = MEMORY_ASSETS.parent/'user'
ABI_PROBE_PROFILE = 'ring0-abi-probe-0.1'
ABI_PROBE_ASSETS = MEMORY_ASSETS.parents[1]/'syscalls'
HOT_UNMAP_PROFILE = 'ring0-hot-unmap-0.1'
HOT_UNMAP_ASSETS = PAGING_ASSETS/'revoke'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_lines(source, operation):
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
    if operation:
        prefix += [operation, '(', ')', ';']
    require([v for v, line in tokens] == prefix + ['cpu_halt', '(', ')', ';', '}'], 'STOP-SOURCE-GRAMMAR')
    return tokens[len(prefix)][1], tokens[6][1] if operation else None


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'STOP-IR-DUPLICATE')
        result[key] = value
    return result


def verify(source_path, hex_path, ir_path, *, identify=False, context=False, fault=False, memory=False, cycle=False, paging=False, user_fault=False, abi_probe=False, hot_unmap=False):
    require(sum((identify,context,fault,memory,cycle,paging,user_fault,abi_probe,hot_unmap)) <= 1, 'STOP-PROFILE-CONFLICT')
    hex_limit = 4096 if abi_probe or hot_unmap else 2304 if user_fault else 1536 if cycle or paging else 1024 if memory else 512 if fault else 256 if context else 128
    for path, limit in [(source_path, 65536), (hex_path, hex_limit), (ir_path, 4096)]:
        require(path.stat().st_size <= limit, 'STOP-INPUT-SIZE')
    source = source_path.read_bytes()
    operation = ('boot_hot_unmap' if hot_unmap else 'boot_abi_probe' if abi_probe else 'boot_user_fault' if user_fault else
                 'boot_paging' if paging else 'boot_frame_cycle' if cycle else
                 'boot_memory' if memory else 'boot_fault' if fault else 'boot_stack' if context else
                 'cpu_identify' if identify else None)
    line, operation_line = source_lines(source, operation)
    ir = json.loads(ir_path.read_text(encoding='ascii'), object_pairs_hook=no_duplicates)
    expected = dict(Schema=3, Target='x86_64', ABI='ring0-stop', Profile=PROFILE,
                    Entry='kernel_main', RequiredCPL=0, Effects=['mask-interrupts', 'halt'],
                    Terminal=dict(Line=line, Offset=0), BodyBytes=4)
    vector = bytes([250, 244, 235, 253])
    mapping = [(line, 0, 1, 'cli'), (line, 1, 1, 'hlt'), (line, 2, 2, 'jmp-hlt')]
    if identify:
        expected = dict(Schema=4, Target='x86_64', ABI='ring0-cpu', Profile=CPU_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Identification=dict(Line=operation_line, Offset=1, Leaf=0),
                        Terminal=dict(Line=line, Offset=5), BodyBytes=8)
        vector = bytes.fromhex('FA 31 C0 0F A2 F4 EB FD')
        mapping = [(operation_line, 0, 1, 'cli'), (operation_line, 1, 2, 'xor-eax'),
                   (operation_line, 3, 2, 'cpuid'), (line, 5, 1, 'hlt'), (line, 6, 2, 'jmp-hlt')]
    if context:
        expected = dict(Schema=5, Target='x86_64', ABI='ring0-context', Profile=CONTEXT_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Stack=dict(Line=operation_line, Low=0x13000, Top=0x14000),
                        Terminal=dict(Line=line, Offset=47), BodyBytes=50)
        sections = [
            ('cli', 'FA'), ('save-rsp-in-rsi', '48 89 E6'), ('clear-status', '31 C0'),
            ('compare-rdi-rbp', '48 39 EF'), ('reject-pointer', '75 24'),
            ('load-context-signature', '48 B9 4D 45 54 41 4C 36 34 21'),
            ('compare-signature', '48 39 0F'), ('reject-signature', '75 15'),
            ('compare-exit-boot-services', '83 7F 78 01'), ('reject-boot-state', '75 0F'),
            ('select-stack-top', '48 8D A7 00 40 01 00'), ('push-marker', '68 42 4D 4F 32'),
            ('pop-marker-to-rdx', '5A'), ('accept-status', 'FF C0'),
            ('hlt', 'F4'), ('jmp-hlt', 'EB FD'),
        ]
        vector, mapping = b'', []
        for kind, hex_bytes in sections:
            instruction = bytes.fromhex(hex_bytes)
            mapping.append((line if kind in ('hlt', 'jmp-hlt') else operation_line,
                            len(vector), len(instruction), kind))
            vector += instruction
    if fault:
        expected = dict(Schema=7, Target='x86_64', ABI='ring0-fault', Profile=FAULT_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Fault=dict(Line=operation_line,Vector=6,Trigger=122,Handler=126,IdtOffset=81920,IdtLimit=111),
                        Terminal=dict(Line=line,Offset=135),BodyBytes=138)
        vector = bytes.fromhex((FAULT_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 138 and vector[122:124] == b'\x0f\x0b', 'FAULT-REFERENCE')
        mapping = [(line if a == 135 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,32,'handoff-guard'),(32,53,'stack-idt-handler-addresses'),(53,97,'idt-gate-6'),
                    (97,122,'lidt'),(122,126,'ud2'),(126,135,'record-fault'),(135,138,'halt')]]
    if memory:
        expected = dict(Schema=8, Target='x86_64', ABI='ring0-memory', Profile=MEMORY_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Frame=dict(Line=operation_line, MapOffset=4096, PageBytes=4096, LimitExclusive=268435456),
                        Terminal=dict(Line=line, Offset=214), BodyBytes=217)
        vector = bytes.fromhex((MEMORY_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 217 and vector[214:] == b'\xf4\xeb\xfd', 'MEMORY-REFERENCE')
        mapping = [(line if a == 214 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,45,'handoff-guard'),(45,114,'map-geometry'),(114,181,'frame-selection'),
                    (181,203,'frame-marker'),(203,214,'next-descriptor'),(214,217,'halt')]]
    if cycle:
        expected = dict(Schema=9, Target='x86_64', ABI='ring0-frame-cycle', Profile=CYCLE_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Pool=dict(Line=operation_line, Capacity=1, PageBytes=4096,
                                  LimitExclusive=268435456, ScrubOnRelease=True),
                        Terminal=dict(Line=line, Offset=425), BodyBytes=474)
        vector = bytes.fromhex((CYCLE_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 474 and vector[425:428] == b'\xf4\xeb\xfd', 'FRAME-CYCLE-REFERENCE')
        mapping = [(line if a == 425 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,51,'handoff-guard'),(51,128,'map-geometry'),(128,223,'frame-selection'),
                    (223,410,'exercise-ownership'),(410,425,'next-descriptor'),(425,428,'halt'),
                    (428,442,'allocate'),(442,472,'release-and-scrub'),(472,474,'deny')]]
    if paging:
        expected = dict(Schema=10, Target='x86_64', ABI='ring0-paging', Profile=PAGING_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Paging=dict(Line=operation_line, TableFrames=5, DataFrames=1, PageBytes=4096,
                                    IdentityLimitExclusive=268435456, Alias=1073741824, AliasUserReadOnlyNX=True),
                        Terminal=dict(Line=line, Offset=470), BodyBytes=473)
        vector = bytes.fromhex((PAGING_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 473 and vector[470:] == b'\xf4\xeb\xfd', 'PAGING-REFERENCE')
        mapping = [(line if a == 470 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,113,'handoff-and-cpu-guard'),(113,190,'map-geometry'),(190,284,'select-six-frames'),
                    (284,389,'link-page-tables'),(389,415,'map-identity-and-seed'),(415,470,'activate-and-read'),
                    (470,473,'halt')]]
    if user_fault:
        expected = dict(Schema=11, Target='x86_64', ABI='ring0-user-fault', Profile=USER_FAULT_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Process=dict(Line=operation_line, Entry=0x40000000, StackTop=0x40002000,
                                     FaultAddress=0x100000, ErrorCode=5, Handler=536, ReclaimedPages=2),
                        Terminal=dict(Line=line, Offset=661), BodyBytes=716)
        vector = bytes.fromhex((USER_FAULT_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 716 and vector[661:664] == b'\xf4\xeb\xfd', 'USER-FAULT-REFERENCE')
        mapping = [(line if a == 661 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,113,'handoff-and-cpu-guard'),(113,273,'map-and-copy-user-program'),
                    (273,475,'gdt-tss-idt'),(475,536,'iretq-to-user'),(536,605,'page-fault-handler'),
                    (605,661,'unmap-and-scrub-user-pages'),(661,664,'halt'),
                    (664,696,'gdt-template'),(696,716,'user-program')]]
    if abi_probe:
        expected = dict(Schema=12, Target='x86_64', ABI='ring0-abi-probe', Profile=ABI_PROBE_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        SBEF=dict(Line=operation_line, Offset=1071, Bytes=168, AbiVersion=1),
                        Portal=dict(Offset=898, Invoke=0, Wait=1, ExpectedCalls=3),
                        Terminal=dict(Line=line, Offset=895), BodyBytes=1239)
        vector = bytes.fromhex((ABI_PROBE_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 1239 and vector[895:898] == b'\xf4\xeb\xfd', 'ABI-PROBE-REFERENCE')
        mapping = [(line if a == 895 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,121,'handoff-and-cpu-guard'),(121,260,'user-mappings'),(260,416,'sbef-admission'),
                    (416,618,'gdt-tss-idt'),(618,709,'syscall-msrs'),(709,770,'iretq-to-user'),
                    (770,839,'page-fault-handler'),(839,895,'unmap-and-scrub'),(895,898,'halt'),
                    (898,1039,'syscall-dispatch'),(1039,1071,'gdt-template'),(1071,1239,'embedded-sbef')]]
    if hot_unmap:
        expected = dict(Schema=13, Target='x86_64', ABI='ring0-hot-unmap', Profile=HOT_UNMAP_PROFILE,
                        Entry='kernel_main', RequiredCPL=0,
                        Revocation=dict(Line=operation_line, Address=0x40002000, PageBytes=4096,
                                        FaultHandler=555, JournalOffset=0x7300, JournalRecords=2),
                        Terminal=dict(Line=line, Offset=865), BodyBytes=930)
        vector = bytes.fromhex((HOT_UNMAP_ASSETS/'expected.hex').read_text(encoding='ascii'))
        require(len(vector) == 930 and vector[865:868] == b'\xf4\xeb\xfd', 'HOT-UNMAP-REFERENCE')
        mapping = [(line if a == 865 else operation_line,a,b-a,kind) for a,b,kind in
                   [(0,113,'handoff-guard'),(113,292,'user-mappings'),(292,494,'gdt-tss-idt'),
                    (494,555,'iretq-to-user'),(555,686,'first-fault'),(686,745,'revoke-and-resume'),
                    (745,809,'second-fault'),(809,865,'process-cleanup'),(865,868,'halt'),
                    (868,900,'gdt-template'),(900,930,'user-program')]]
    require(json.dumps(ir, sort_keys=True) == json.dumps(expected, sort_keys=True), 'STOP-IR')
    tokens = hex_path.read_text(encoding='ascii').split()
    require(len(tokens) == len(vector) and all(re.fullmatch('[0-9A-Fa-f]{2}', t) for t in tokens), 'STOP-HEX')
    body = bytes(int(t, 16) for t in tokens)
    # Independent manual instruction vector: no import of compiler or profile table.
    require(body == vector, 'STOP-EMISSION')
    packet = b'FAGRAW64' + struct.pack('<IIII', len(body), 0, sum(body), 0) + body
    report = dict(Schema=1, Verified=True, Target='x86_64', ABI=expected['ABI'], Profile=expected['Profile'],
                  BodyBytes=len(body), PacketBytes=len(packet), Integers=[],
                  Mapping=[dict(Line=ln, Offset=o, Bytes=n, Kind=k) for ln, o, n, k in mapping],
                  Scope='Closed source grammar and exact emission; CPL0 required; QEMU evidence separate.')
    if user_fault or abi_probe or hot_unmap:
        require(len(packet) <= 4096, 'BRIDGE-BUDGET')
        report['BridgePacketLimitBytes'] = 4096
    else:
        report['EntryBudget'] = entry_budget(len(body), len(packet))
    for key, data in [('Source', source), ('Hex', hex_path.read_bytes()),
                      ('IR', ir_path.read_bytes()), ('Packet', packet)]:
        report[key + 'SHA256'] = hashlib.sha256(data).hexdigest()
    return packet, report


def check(run, *, identify=False, context=False, fault=False, memory=False, cycle=False, paging=False, user_fault=False, abi_probe=False, hot_unmap=False):
    root = Path(__file__).resolve().parents[1]
    packet, report = verify(run/'source.casm', run/'program.hex', run/'program.ir.json',
                            identify=identify, context=context, fault=fault, memory=memory, cycle=cycle, paging=paging,
                            user_fault=user_fault, abi_probe=abi_probe, hot_unmap=hot_unmap)
    source = HOT_UNMAP_ASSETS/'main.casm' if hot_unmap else ABI_PROBE_ASSETS/'main.casm' if abi_probe else USER_FAULT_ASSETS/'main.casm' if user_fault else PAGING_ASSETS/'main.casm' if paging else CYCLE_ASSETS/'main.casm' if cycle else MEMORY_ASSETS/'main.casm' if memory else FAULT_ASSETS/'main.casm' if fault else root / ('kernel/boot/context/main.casm' if context else
                     'kernel/arch/x86_64/cpu/identify.casm' if identify else 'kernel/boot/stop/main.casm')
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
    profile = p.add_mutually_exclusive_group()
    profile.add_argument('--identify', action='store_true')
    profile.add_argument('--context', action='store_true')
    profile.add_argument('--fault', action='store_true')
    profile.add_argument('--memory', action='store_true')
    profile.add_argument('--frame-cycle', action='store_true')
    profile.add_argument('--paging', action='store_true')
    profile.add_argument('--user-fault', action='store_true')
    profile.add_argument('--abi-probe', action='store_true')
    profile.add_argument('--hot-unmap', action='store_true')
    args = p.parse_args()
    outputs = [args.packet.resolve(), args.report.resolve()]
    require(len(set(outputs)) == 2 and not set(outputs).intersection(
            path.resolve() for path in [args.source, args.hex, args.ir, FAULT_ASSETS/'expected.hex',
                                        MEMORY_ASSETS/'expected.hex', CYCLE_ASSETS/'expected.hex',
                                        PAGING_ASSETS/'expected.hex', USER_FAULT_ASSETS/'expected.hex',
                                        ABI_PROBE_ASSETS/'expected.hex', HOT_UNMAP_ASSETS/'expected.hex']), 'STOP-OUTPUT-ALIAS')
    packet, report = verify(args.source, args.hex, args.ir, identify=args.identify, context=args.context,
                            fault=args.fault, memory=args.memory, cycle=args.frame_cycle, paging=args.paging,
                            user_fault=args.user_fault, abi_probe=args.abi_probe, hot_unmap=args.hot_unmap)
    args.packet.write_bytes(packet)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(f'GREEN [STOP-VERIFY] {report["BodyBytes"]} body bytes; {len(packet)} packet bytes independently checked.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, TypeError) as error:
        raise SystemExit(f'RED [STOP-VERIFY] {error}') from error
