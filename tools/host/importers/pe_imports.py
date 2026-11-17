"""Bounded, read-only inventory of regular PE32+ imports."""
import struct

from ..diagnostics import Rejection


DESCRIPTOR = struct.Struct('<IIIII')
THUNK = struct.Struct('<Q')
MAX_LIBRARIES = 128
MAX_SYMBOLS = 4096
MAX_NAME = 256


def inventory_imports(data, sections, directory, directory_offset):
    def locate(rva, size, source, field):
        matches = []
        for section in sections:
            delta = rva - section['RVA']
            limit = min(section['VirtualBytes'], section['FileBytes'])
            if 0 <= delta and delta + size <= limit:
                matches.append((section['FileOffset'] + delta, limit - delta))
        if len(matches) != 1:
            raise Rejection('PE-IMPORT-RVA', source, field)
        return matches[0]

    def name(rva, skip, source, field):
        offset, available = locate(rva, skip + 1, source, field)
        start = offset + skip
        end = data.find(b'\0', start, start + min(available - skip, MAX_NAME + 1))
        if end <= start or any(not 0x21 <= byte < 0x7f for byte in data[start:end]):
            raise Rejection('PE-IMPORT-NAME', start, field)
        return data[start:end].decode('ascii')

    size = directory['Bytes']
    if size < DESCRIPTOR.size:
        raise Rejection('PE-IMPORT-TABLE', directory_offset, 'DataDirectory.imports')
    table, _ = locate(directory['RVA'], size, directory_offset, 'DataDirectory.imports')
    libraries = []
    total = 0
    for index in range(min(size // DESCRIPTOR.size, MAX_LIBRARIES + 1)):
        at = table + index * DESCRIPTOR.size
        lookup, timestamp, forwarder, module, iat = DESCRIPTOR.unpack_from(data, at)
        if not (lookup or timestamp or forwarder or module or iat):
            return libraries
        if index == MAX_LIBRARIES:
            raise Rejection('PE-IMPORT-LIMIT', at, 'ImportDescriptors')
        if not module or not iat or (not lookup and timestamp):
            raise Rejection('PE-IMPORT-DESCRIPTOR', at, 'ImportDescriptor')
        dll = name(module, 0, at + 12, 'Name')
        cursor, available = locate(lookup or iat, THUNK.size, at, 'OriginalFirstThunk/FirstThunk')
        symbols = []
        for slot in range(available // THUNK.size):
            entry = cursor + slot * THUNK.size
            value, = THUNK.unpack_from(data, entry)
            if not value:
                break
            if total == MAX_SYMBOLS:
                raise Rejection('PE-IMPORT-LIMIT', entry, 'ImportLookup')
            if value >> 63:
                if value & 0x7fffffffffff0000:
                    raise Rejection('PE-IMPORT-ORDINAL', entry, 'ImportLookup')
                symbols.append(dict(Ordinal=value & 0xffff))
            else:
                symbols.append(dict(Name=name(value, 2, entry, 'ImportByName')))
            total += 1
        else:
            raise Rejection('PE-IMPORT-TERMINATOR', cursor, 'ImportLookup')
        libraries.append(dict(DLL=dll, Symbols=symbols))
    raise Rejection('PE-IMPORT-TERMINATOR', table, 'ImportDescriptors')
