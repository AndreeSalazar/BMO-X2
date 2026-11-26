"""Materialize the fixed Win64 single-module TLS profile for a two-thread probe."""
import struct

from ..diagnostics import Rejection


TLS_BASES = (0x40E00000, 0x40E01000)
TLS_VECTOR = 0x100
TLS_STORAGE = 0x200
TLS_DIRECTORY = struct.Struct('<QQQQII')
TLS_PROFILE = {
    'Name': 'win64-static-tls-v1',
    'AbiVersion': 1,
    'Scope': 'One static PE32+ TLS template, no callbacks, two fresh QEMU threads',
}


def tls_regions(image, sections, opt):
    directory = image['Directories'].get('tls')
    diagnostic = opt + 184
    if not directory or directory['Bytes'] != TLS_DIRECTORY.size:
        raise Rejection('PE-TLS-DIRECTORY', diagnostic, 'DataDirectory.tls')

    def read(address, size, permissions, field):
        matches = [data[address - start:address - start + size]
                   for start, data, _, flags in sections
                   if flags in permissions and start <= address <= start + len(data) - size]
        if len(matches) != 1:
            raise Rejection('PE-TLS-RANGE', diagnostic, field)
        return matches[0]

    address = image['ImageBase'] + directory['RVA']
    start, end, index, callbacks, zero_fill, characteristics = TLS_DIRECTORY.unpack(
        read(address, TLS_DIRECTORY.size, (4,), 'TLS.Directory'))
    if start >= end or end - start + zero_fill > 512 or characteristics not in (0, 0x00400000):
        raise Rejection('PE-TLS-LAYOUT', diagnostic, 'TLS.Template/SizeOfZeroFill/Characteristics')
    if index % 4 or read(index, 4, (6,), 'TLS.AddressOfIndex') != bytes(4):
        raise Rejection('PE-TLS-INDEX', diagnostic, 'TLS.AddressOfIndex')
    if callbacks and read(callbacks, 8, (4,), 'TLS.AddressOfCallbacks') != bytes(8):
        raise Rejection('PE-TLS-CALLBACK', diagnostic, 'TLS.AddressOfCallbacks')
    template = read(start, end - start, (4, 6), 'TLS.Template')
    regions = []
    for base in TLS_BASES:
        payload = bytearray(TLS_STORAGE)
        struct.pack_into('<Q', payload, 0x58, base + TLS_VECTOR)
        struct.pack_into('<Q', payload, TLS_VECTOR, base + TLS_STORAGE)
        payload.extend(template)
        regions.append((base, bytes(payload), len(payload) + zero_fill, 6))
    return regions, dict(Profile=TLS_PROFILE['Name'], TemplateBytes=len(template), ZeroFillBytes=zero_fill,
                         Index=0, ThreadBases=[f'0x{base:X}' for base in TLS_BASES])
