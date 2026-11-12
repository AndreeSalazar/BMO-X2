"""Change only the embedded SBEF and repair the outer test packet checksum."""
import struct


SBEF_OFFSET = 24 + 1071
MUTATIONS = {'sbef-abi': (6, 2, 1), 'sbef-permisos': (52, 7, 5)}


def mutated_packet(packet, case):
    offset, value, expected = MUTATIONS[case]
    if len(packet) != 1263 or packet[:8] != b'FAGRAW64' or packet[SBEF_OFFSET:SBEF_OFFSET+4] != b'SBEF':
        raise ValueError('ABI-PROBE: paquete de referencia invalido')
    field = SBEF_OFFSET + offset
    if struct.unpack_from('<H', packet, field)[0] != expected:
        raise ValueError('ABI-PROBE: cambio el campo a mutar')
    changed = bytearray(packet)
    struct.pack_into('<H', changed, field, value)
    struct.pack_into('<I', changed, 16, sum(changed[24:]))
    return bytes(changed)
