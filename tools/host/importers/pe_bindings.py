"""Bind the MSVC session fixture's one supported import."""
import struct

from ..diagnostics import Rejection
from .pe_imports import inventory_imports


def bind_session_clock(data, image, opt, segments, clock_target):
    directory = image['Directories'].get('imports')
    iat = image['Directories'].get('iat')
    if directory is None or iat is None:
        raise Rejection('PE-CLOCK-IMPORT', opt + 120, 'DataDirectory.imports/iat')
    libraries = inventory_imports(data, image['Sections'], directory, opt + 120, include_slots=True)
    if (len(libraries) != 1 or libraries[0]['DLL'].lower() != 'kernel32.dll'
            or len(libraries[0]['Symbols']) != 1
            or libraries[0]['Symbols'][0].get('Name') != 'GetTickCount64'):
        raise Rejection('PE-CLOCK-IMPORT', opt + 120, 'KERNEL32.dll!GetTickCount64')
    symbol = libraries[0]['Symbols'][0]
    text, readonly, _ = segments
    if not text[0] <= clock_target < text[0] + len(text[1]):
        raise Rejection('PE-CLOCK-TARGET', opt + 16, 'ClockTarget')
    rva = symbol['IatRVA']
    offset = image['ImageBase'] + rva - readonly[0]
    if (iat != dict(RVA=rva, Bytes=16) or rva % 8 or not 0 <= offset <= len(readonly[1]) - 16
            or struct.unpack_from('<QQ', readonly[1], offset) != (symbol['LookupValue'], 0)):
        raise Rejection('PE-IAT-LAYOUT', opt + 208, 'DataDirectory.iat')
    payload = bytearray(readonly[1])
    struct.pack_into('<Q', payload, offset, clock_target)
    segments[1] = readonly[0], bytes(payload), readonly[2], readonly[3]
