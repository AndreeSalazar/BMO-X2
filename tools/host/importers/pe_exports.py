"""Read bounded named code exports for the fixed Win64 DLL profiles."""
import struct

from ..diagnostics import Rejection


EXPORT_DIRECTORY = struct.Struct('<IIHHIIIIIII')
FIXED_DLL_PROFILE = {
    'Name': 'win64-fixed-dll-v1',
    'AbiVersion': 1,
    'Scope': 'One entryless fixed PE32+ DLL and one direct named code export, bound by HOST',
}
DLL_LIFECYCLE_PROFILE = {
    'Name': 'win64-fixed-dll-lifecycle-v1',
    'AbiVersion': 1,
    'Scope': 'One fixed PE32+ DLL with a checked entry export and explicit Ring 3 startup',
}
DLL_ENTRY_EXPORT = 'BmoDllEntry'
DLL_LIFECYCLE_BASE = 0x40800000


def code_exports(image, segments, opt, count):
    directory = image['Directories'].get('exports')
    if not directory:
        raise Rejection('PE-DLL-EXPORT', opt + 112, 'DataDirectory.exports')
    base = image['ImageBase']
    start, size = directory['RVA'], directory['Bytes']
    end = start + size
    tables = [(address - base, payload) for address, payload, _, perms in segments
              if perms == 4 and address - base <= start < end <= address - base + len(payload)]
    if len(tables) != 1 or size < EXPORT_DIRECTORY.size:
        raise Rejection('PE-DLL-EXPORT', opt + 112, 'DataDirectory.exports')
    rva, data = tables[0]

    def take(address, length):
        if not start <= address <= end - length:
            raise Rejection('PE-DLL-EXPORT-RANGE', opt + 112, 'ExportDirectory.RVA')
        return data[address - rva:address - rva + length]

    def name(address):
        limit = min(256, end - address)
        if limit <= 1:
            raise Rejection('PE-DLL-EXPORT-NAME', opt + 112, 'ExportDirectory.Name')
        field, zero, _ = take(address, limit).partition(b'\0')
        if not zero or not field or any(not 0x21 <= byte <= 0x7e for byte in field):
            raise Rejection('PE-DLL-EXPORT-NAME', opt + 112, 'ExportDirectory.Name')
        return field.decode('ascii')

    _, _, _, _, dll_name, ordinal_base, functions, names, eat, names_rva, ordinals = (
        EXPORT_DIRECTORY.unpack(take(start, EXPORT_DIRECTORY.size)))
    if (ordinal_base, functions, names) != (1, count, count):
        raise Rejection('PE-DLL-EXPORT-COUNT', opt + 112, 'ExportDirectory.NumberOfNames')
    ordinals = struct.unpack(f'<{count}H', take(ordinals, 2 * count))
    if sorted(ordinals) != list(range(count)):
        raise Rejection('PE-DLL-EXPORT-COUNT', opt + 112, 'ExportDirectory.AddressOfNameOrdinals')
    rvas = struct.unpack(f'<{count}I', take(eat, 4 * count))
    name_rvas = struct.unpack(f'<{count}I', take(names_rva, 4 * count))
    exports = {}
    for ordinal, symbol_rva in zip(ordinals, name_rvas):
        export_rva = rvas[ordinal]
        if start <= export_rva < end:
            raise Rejection('PE-DLL-FORWARDER', opt + 112, 'ExportDirectory.AddressOfFunctions')
        target = base + export_rva
        if not any(perms == 5 and address <= target < address + len(payload)
                   for address, payload, _, perms in segments):
            raise Rejection('PE-DLL-EXPORT-TARGET', opt + 112, 'ExportDirectory.AddressOfFunctions')
        symbol = name(symbol_rva)
        if symbol in exports:
            raise Rejection('PE-DLL-EXPORT-NAME', opt + 112, 'ExportDirectory.AddressOfNames')
        exports[symbol] = target
    library = name(dll_name)
    if not library.lower().endswith('.dll') or any(char in library for char in '/\\:'):
        raise Rejection('PE-DLL-EXPORT-NAME', opt + 112, 'ExportDirectory.Name')
    return library, exports
