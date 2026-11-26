"""Inspect selected PE32+ load configuration fields without admitting them."""

import struct

from ..diagnostics import Rejection


GUARD_FLAGS = {
    0x100: 'CF_INSTRUMENTED',
    0x200: 'CFW_INSTRUMENTED',
    0x400: 'CF_FUNCTION_TABLE_PRESENT',
    0x800: 'SECURITY_COOKIE_UNUSED',
    0x10000: 'CF_LONGJUMP_TABLE_PRESENT',
    0x400000: 'EH_CONTINUATION_TABLE_PRESENT',
    0x800000: 'XFG_ENABLED',
}


def inventory_load_config(data, sections, directory, image_base, directory_offset):
    rva, directory_size = directory['RVA'], directory['Bytes']
    matches = [section for section in sections if section['RVA'] <= rva
               and rva + directory_size <= section['RVA'] + min(
                   section['VirtualBytes'] or section['FileBytes'], section['FileBytes'])]
    if directory_size < 4 or len(matches) != 1:
        raise Rejection('PE-LOAD-CONFIG-INVENTORY-RANGE', directory_offset, 'DataDirectory.load_config')
    section = matches[0]
    start = section['FileOffset'] + rva - section['RVA']
    size, = struct.unpack_from('<I', data, start)
    if not 4 <= size <= directory_size:
        raise Rejection('PE-LOAD-CONFIG-INVENTORY-SIZE', start, 'LoadConfig.Size')

    def field(offset, kind):
        if offset + struct.calcsize(kind) <= size:
            return struct.unpack_from(kind, data, start + offset)[0]
        return None

    cookie = field(88, '<Q')
    cookie_rva = cookie - image_base if cookie and cookie >= image_base else None
    cookie_sections = [item for item in sections if cookie_rva is not None and item['RVA'] <= cookie_rva
                       and cookie_rva + 8 <= item['RVA'] + (item['VirtualBytes'] or item['FileBytes'])]
    cookie_writable = (len(cookie_sections) == 1 and cookie_sections[0]['Writable']
                       and not cookie_sections[0]['Executable'])
    flags = field(144, '<I')
    return dict(
        Size=size, DirectoryBytes=directory_size,
        SecurityCookieVA=cookie, SecurityCookieRVA=cookie_rva,
        SecurityCookieWritableNonExecutable=cookie_writable,
        GuardFlags=flags, RecognizedGuardFlags=[name for mask, name in GUARD_FLAGS.items() if (flags or 0) & mask],
        GuardCFCheckFunctionPointerVA=field(112, '<Q'), GuardCFDispatchFunctionPointerVA=field(120, '<Q'),
        GuardCFFunctionTableVA=field(128, '<Q'), GuardCFFunctionCount=field(136, '<Q'),
    )
