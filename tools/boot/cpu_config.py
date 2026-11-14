"""Turn observed CPUID leaf zero into a scoped QEMU profile."""
import hashlib
import json
import re
import struct


def register(snapshot, name):
    matches = re.findall(rf'\b{name}\s*=\s*([0-9a-fA-F]+)\b', snapshot)
    if len(matches) != 1:
        raise ValueError(f'CPU-CONFIG: registro ausente o ambiguo {name}')
    return int(matches[0], 16)


def identify(snapshot):
    eax, ebx, edx, ecx = (register(snapshot, name) for name in ('RAX', 'RBX', 'RDX', 'RCX'))
    if any(value > 0xffffffff for value in (eax, ebx, edx, ecx)):
        raise ValueError('CPU-CONFIG: CPUID excede 32 bits')
    vendor = struct.pack('<III', ebx, edx, ecx)
    if not vendor.strip() or any(value < 32 or value > 126 for value in vendor):
        raise ValueError('CPU-CONFIG: fabricante invalido')
    return dict(Vendor=vendor.decode('ascii'), MaxBasicLeaf=eax)


def l1_cache_profile(raw):
    leaf, data_b, data_c, code_b, code_c, unified_b, unified_c, present = struct.unpack('<8I', raw)
    if leaf not in (0, 4, 0x8000001d) or present & ~7 or (not leaf and present):
        raise ValueError('CPU-CONFIG: perfil L1 invalido')
    profile = dict(Leaf=f'0x{leaf:X}' if leaf else None)
    for index, (name, ebx, ecx) in enumerate((
        ('Data', data_b, data_c), ('Instruction', code_b, code_c), ('Unified', unified_b, unified_c),
    )):
        if not present & (1 << index):
            profile[name] = None
            continue
        line_bytes = (ebx & 0xfff) + 1
        partitions = ((ebx >> 12) & 0x3ff) + 1
        ways = (ebx >> 22) + 1
        sets = ecx + 1
        profile[name] = dict(Bytes=line_bytes * partitions * ways * sets, LineBytes=line_bytes,
                             Ways=ways, Sets=sets, Partitions=partitions)
    return profile


def write_config(run, result, environment, verified):
    cases = result.get('Cases')
    if result.get('Passed') != 1 or result.get('Total') != 1 or not isinstance(cases, list) or len(cases) != 1:
        raise ValueError('CPU-CONFIG: falta la prueba normal de identificacion')
    case = cases[0]
    if (case.get('Case'), case.get('Passed'), case.get('BootServicesExited'),
            case.get('PayloadReturned'), case.get('Ring'), case.get('OwnHalt'),
            case.get('InterruptsMasked'), case.get('InstructionPointerOffset')) != (
                'normal', True, True, False, 0, True, True, 6):
        raise ValueError('CPU-CONFIG: la ejecucion no cumple el contrato')
    code = (run/'build/puente-normal-code.bin').read_bytes()
    packet = (run/'INICIO.X86').read_bytes()
    if (code != packet[24:] or len(code) != verified['BodyBytes']
            or hashlib.sha256(packet).hexdigest() != verified['PacketSHA256']
            or environment['packet_sha256'] != verified['PacketSHA256']
            or verified['Profile'] != 'ring0-cpu-0.1'):
        raise ValueError('CPU-CONFIG: imagen ejecutada distinta de la verificada')
    observed = identify((run/'build/puente-normal-registers.txt').read_text(encoding='ascii'))
    if observed != case.get('CPUIdentification'):
        raise ValueError('CPU-CONFIG: registros e informe distintos')
    lines = [
        'PROFILE_SCHEMA=1',
        'PROFILE_SOURCE=QEMU_CPUID_LEAF_0',
        'TARGET=x86_64',
        f'CPU_VENDOR={json.dumps(observed["Vendor"])}',
        f'CPU_MAX_BASIC_LEAF=0x{observed["MaxBasicLeaf"]:08X}',
        f'PACKET_SHA256={verified["PacketSHA256"]}',
        '',
    ]
    output = run/'profile.config'
    pending = run/'profile.config.tmp'
    with pending.open('x', encoding='ascii', newline='\n') as handle:
        handle.write('\n'.join(lines))
    pending.replace(output)
    return output
