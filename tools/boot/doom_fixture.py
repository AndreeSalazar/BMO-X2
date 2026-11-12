"""Build a DOOM-specific copy of the frozen single-page CASM ABI fixture."""
import hashlib
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sbef_host.format import inspect

from sbef_probe_cases import SBEF_OFFSET


def make_packet(reference, image):
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
    payload = image[64:]
    marker = payload.find(completion)
    if marker < 0 or payload.count(completion) != 1:
        raise ValueError('Falta el terminal de comprobacion DOOM')
    fault_rip = 0x40000000 + marker + len(completion) - 4
    packet = bytearray(reference[:SBEF_OFFSET] + image)
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
    struct.pack_into('<I', packet, 8, len(packet) - 24)
    struct.pack_into('<I', packet, 16, sum(packet[24:]))
    return bytes(packet), dict(fault_rip=fault_rip, sbef_bytes=len(image),
                               sbef_sha256=hashlib.sha256(image).hexdigest())
