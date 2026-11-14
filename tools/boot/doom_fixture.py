"""Build a DOOM-specific copy of the frozen single-page CASM ABI fixture."""
import hashlib
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from host.sbef.format import inspect

from sbef_probe_cases import SBEF_OFFSET


EXTERNAL_ADDRESS = 0x2000000


def make_packet(reference, image, desktop_present=None, session_gate=None, external=None, *, engine=False,
                reuse=None):
    if external is not None:
        if session_gate is None:
            raise ValueError('El cargador externo requiere el perfil de sesion')
        # The guest validates the independent file. Use only the original
        # frozen fixture to construct the kernel packet.
        image = reference[SBEF_OFFSET:]
    report = inspect(image)
    regions = report['Regions']
    if report['AbiVersion'] != 1 or len(regions) != 1:
        raise ValueError('DOOM requiere ABI 1 y una region RX')
    region = regions[0]
    size = region['FileBytes']
    entry = int(report['Entry'], 16)
    if (region['Address'], region['Offset'], region['MemoryBytes'], region['Permissions']) != (
            '0x40000000', 64, size, 'RX') or len(image) + SBEF_OFFSET > 4096:
        raise ValueError('DOOM excede la disposicion de la sonda CASM')
    completion = bytes.fromhex('bc0020004048b8424d55534552332150bb000010008b0b0f0b')
    if desktop_present is not None:
        completion = bytes.fromhex('4989ff') + completion
    payload = image[64:]
    marker = payload.find(completion)
    if session_gate is None and (marker < 0 or payload.count(completion) != 1):
        raise ValueError('Falta el terminal de comprobacion DOOM')
    fault_rip = 0x40000000 + marker + len(completion) - 4
    packet = bytearray(reference[:SBEF_OFFSET] + (image if external is None else b''))
    for offset, old, new in [
        (302, 'a8000000', struct.pack('<I', len(image))),
        (316, '00000040', struct.pack('<I', entry)),
        # CMP ECX,imm32; JNE to the existing rejection branch at 386; NOP.
        (364, '83f9680f850a020000', b'\x81\xf9' + struct.pack('<I', size) + bytes.fromhex('750e90')),
        (764, '00000040', struct.pack('<I', entry)),
        (800, '64000040', struct.pack('<I', fault_rip)),
    ]:
        at = 24 + offset
        expected = bytes.fromhex(old)
        if packet[at:at + len(expected)] != expected:
            raise ValueError(f'Cambio el vector CASM en {offset}')
        packet[at:at + len(expected)] = new
    if desktop_present is not None:
        at = 24 + 889
        if packet[at:at + 6] != bytes.fromhex('41bc01000000'):
            raise ValueError('Cambio el terminal de salida ABI')
        packet[at:at+6] = b'\xe9' + struct.pack('<i', len(packet) - at - 5) + b'\x90'
        packet.extend(desktop_present)
        packet.extend(b'\xe9' + struct.pack('<i', 24 + 895 - len(packet) - 5))
    if reuse is not None:
        code, second = reuse
        second_packet, second_info = make_packet(reference, second)
        if second_info['fault_rip'] != fault_rip or image == second:
            raise ValueError('Reuso ABI requiere dos clientes distintos con el mismo terminal')
        at = 24 + 889
        if packet[at:at+6] != bytes.fromhex('41bc01000000'):
            raise ValueError('Cambio el terminal ABI')
        packet[at:at+6] = b'\xe9' + struct.pack('<i', len(packet) - at - 5) + b'\x90'
        # The fixed stage ends immediately before its second SBEF.
        # A return jump is stored after the stage and before the second SBEF.
        if code[-5:] != b'\xe9\x00\x00\x00\x00':
            raise ValueError('Falta el salto de retorno de reuso ABI')
        packet.extend(code[:-4])
        packet.extend(struct.pack('<i', 24 + 895 - len(packet) - 4))
        packet.extend(second_packet[SBEF_OFFSET:])
    if session_gate is not None:
        # Repoint LSTAR and save the bridge CR3/context before the first IRET.
        at = 24 + 677
        lstar = packet.index(bytes.fromhex('488d05d4000000'), at, at + 18)
        struct.pack_into('<i', packet, lstar + 3, len(packet) - lstar - 7)
        packet.extend(session_gate)
        at = 24 + 709
        original = bytes.fromhex('b9800000c0')
        if packet[at:at+5] != original:
            raise ValueError('Cambio la preparacion de EFER')
        packet[at:at+5] = b'\xe9' + struct.pack('<i', len(packet) - at - 5)
        packet.extend(bytes.fromhex('4d89aa180300004989aa20030000') + original)
        packet.extend(b'\xe9' + struct.pack('<i', at + 5 - len(packet) - 5))
    if external is not None:
        stack = 24 + 754
        if packet[stack:stack+5] != bytes.fromhex('6800200040'):
            raise ValueError('Cambio la pila de usuario')
        packet[stack:stack+5] = bytes.fromhex('6800000041' if engine else '6800300040')
        at = 24 + 260
        if packet[at:at+7] != bytes.fromhex('488d3524030000'):
            raise ValueError('Cambio la entrada del validador SBEF')
        packet[at:at+7] = b'\xe9' + struct.pack('<i', len(packet) - at - 5) + b'\x90\x90'
        at = 24 + 763
        if packet[at:at+5] != bytes.fromhex('6800000040'):
            raise ValueError('Cambio la entrada de usuario')
        packet[at:at+5] = bytes.fromhex('4154909090')  # push r12; nop
        packet.extend(external)
        packet.extend(b'\xe9' + struct.pack('<i', 24 + 416 - len(packet) - 5))
    if len(packet) > 4096:
        raise ValueError('El paquete de prueba excede el limite del puente')
    struct.pack_into('<I', packet, 8, len(packet) - 24)
    struct.pack_into('<I', packet, 16, sum(packet[24:]))
    return bytes(packet), dict(fault_rip=fault_rip, sbef_bytes=len(image),
                               sbef_sha256=hashlib.sha256(image).hexdigest(),
                               desktop=desktop_present is not None, session=session_gate is not None,
                               reuse=reuse is not None)


def prepend_intro(packet, splash):
    """Redirect the verified HD intro terminal into the separate ABI probe."""
    intro = bytearray(splash[24:])
    if len(intro) == 1255:
        terminal, lea = 216, bytes.fromhex('488d359d000000')
    elif len(intro) == 484:
        terminal, lea = 213, bytes.fromhex('488d359a000000')
    else:
        raise ValueError('Tamano de intro desconocido')
    if intro[terminal:terminal+3] != b'\xf4\xeb\xfd':
        raise ValueError('Cambio el terminal del gato')
    site = intro.index(lea)
    intro[site+3] += 2  # The longer jump shifts the palette and mask by two bytes.
    intro[terminal:terminal+3] = b'\xe9' + struct.pack('<i', len(intro) - terminal)
    for branch in (8, 18):
        if intro[branch:branch+2] != b'\x0f\x85':
            raise ValueError('Cambio la guarda de entrega del gato HD')
        struct.pack_into('<i', intro, branch+2, len(intro) - branch - 6)
    intro.extend(bytes.fromhex('f4ebfd'))  # Preserve the rejected handoff terminal.
    intro.extend(bytes.fromhex('4889ef'))  # Restore RDI to the bridge context.
    body = intro + packet[24:]
    if len(body) + 24 > 4096:
        raise ValueError('Intro y sonda exceden el limite del puente')
    header = bytearray(packet[:24])
    struct.pack_into('<I', header, 8, len(body))
    struct.pack_into('<I', header, 16, sum(body))
    return bytes(header + body), len(intro)
