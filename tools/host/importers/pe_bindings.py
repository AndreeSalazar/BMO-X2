"""Bind the MSVC session fixture's supported imports."""
import struct

from ..diagnostics import Rejection
from .pe_imports import inventory_imports


SESSION_EXPORTS = {
    'GetTickCount64': 'bmo_session_tick_ms',
    'GetStdHandle': 'bmo_session_stdout',
    'WriteFile': 'bmo_session_write',
}

WIN64_CONSOLE_PROFILE = {
    'Name': 'win64-console-v1',
    'AbiVersion': 1,
    'DLL': 'KERNEL32.dll',
    'Imports': SESSION_EXPORTS,
    'Scope': 'External QEMU console fixture',
}


def bind_session_imports(data, image, opt, segments, bindings):
    directory = image['Directories'].get('imports')
    iat = image['Directories'].get('iat')
    if directory is None or iat is None:
        raise Rejection('PE-SESSION-IMPORT', opt + 120, 'DataDirectory.imports/iat')
    libraries = inventory_imports(data, image['Sections'], directory, opt + 120, include_slots=True)
    if len(libraries) != 1 or libraries[0]['DLL'].lower() != 'kernel32.dll':
        raise Rejection('PE-SESSION-IMPORT', opt + 120, 'DataDirectory.imports')
    symbols = libraries[0]['Symbols']
    names = [symbol.get('Name') for symbol in symbols]
    if not names or len(set(names)) != len(names) or set(names) != set(bindings):
        missing = next((name or 'ordinal' for name in names if name not in bindings), 'ImportLookup')
        raise Rejection('PE-SESSION-IMPORT', opt + 120, f'KERNEL32.dll!{missing}')
    text, readonly, _ = segments
    rva = symbols[0]['IatRVA']
    size = (len(symbols) + 1) * 8
    offset = image['ImageBase'] + rva - readonly[0]
    initial = tuple(symbol['LookupValue'] for symbol in symbols) + (0,)
    if (iat != dict(RVA=rva, Bytes=size) or rva % 8 or not 0 <= offset <= len(readonly[1]) - size
            or struct.unpack_from(f'<{len(initial)}Q', readonly[1], offset) != initial):
        raise Rejection('PE-IAT-LAYOUT', opt + 208, 'DataDirectory.iat')
    payload = bytearray(readonly[1])
    for index, (name, symbol) in enumerate(zip(names, symbols)):
        if symbol['IatRVA'] != rva + index * 8:
            raise Rejection('PE-IAT-LAYOUT', opt + 208, 'DataDirectory.iat')
        target = bindings[name]
        if name not in SESSION_EXPORTS or not text[0] <= target < text[0] + len(text[1]):
            raise Rejection('PE-SESSION-TARGET', opt + 16, f'KERNEL32.dll!{name}')
        struct.pack_into('<Q', payload, offset + index * 8, target)
    segments[1] = readonly[0], bytes(payload), readonly[2], readonly[3]
