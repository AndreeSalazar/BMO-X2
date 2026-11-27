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

WIN64_HEAP_PROFILE = {
    **WIN64_CONSOLE_PROFILE,
    'Name': 'win64-console-heap-v1',
    'Imports': {
        **SESSION_EXPORTS,
        'GetProcessHeap': 'bmo_get_process_heap',
        'HeapAlloc': 'bmo_heap_alloc',
        'HeapFree': 'bmo_heap_free',
        'HeapReAlloc': 'bmo_heap_realloc',
        'HeapSize': 'bmo_heap_size',
    },
    'Scope': 'External QEMU console fixture with a bounded process heap',
}

WIN64_FILE_PROFILE = {
    **WIN64_HEAP_PROFILE,
    'Name': 'win64-package-file-v1',
    'Imports': {
        **WIN64_HEAP_PROFILE['Imports'],
        'CreateFileW': 'bmo_package_open',
        'ReadFile': 'bmo_package_read',
        'CloseHandle': 'bmo_package_close',
        'GetLastError': 'bmo_get_last_error',
        'GetFileType': 'bmo_package_file_type',
        'GetFileSizeEx': 'bmo_package_file_size',
        'SetFilePointerEx': 'bmo_package_seek',
    },
    'Scope': 'External single-threaded QEMU fixture with a read-only package input',
}

WIN64_SCRATCH_FILE_PROFILE = {
    **WIN64_FILE_PROFILE,
    'Name': 'win64-scratch-file-v1',
    'Imports': {
        **WIN64_FILE_PROFILE['Imports'],
        'WriteFile': 'bmo_package_write',
        'SetEndOfFile': 'bmo_package_set_eof',
        'FlushFileBuffers': 'bmo_package_flush',
    },
    'Scope': 'External single-threaded QEMU fixture with a 4 KiB volatile output file',
}

WIN64_PROCESS_PROFILE = {
    **WIN64_CONSOLE_PROFILE,
    'Name': 'win64-process-start-v1',
    'Imports': {
        'GetStdHandle': SESSION_EXPORTS['GetStdHandle'],
        'WriteFile': SESSION_EXPORTS['WriteFile'],
        'GetCommandLineW': 'bmo_get_command_line_w',
        'GetCommandLineA': 'bmo_get_command_line_a',
        'GetStartupInfoW': 'bmo_get_startup_info_w',
        'GetACP': 'bmo_get_acp',
        'GetLastError': 'bmo_get_last_error',
        'SetLastError': 'bmo_set_last_error',
        'ExitProcess': 'bmo_exit_process',
        'TlsAlloc': 'bmo_tls_alloc',
        'TlsFree': 'bmo_tls_free',
        'TlsGetValue': 'bmo_tls_get_value',
        'TlsSetValue': 'bmo_tls_set_value',
        'InitializeSListHead': 'bmo_initialize_slist_head',
    },
    'Scope': 'Single-threaded QEMU startup with UTF-16, UTF-8 ACP, DWORD exit and 64 dynamic TLS slots',
}

WIN64_SESSION_PROFILES = (
    WIN64_CONSOLE_PROFILE, WIN64_HEAP_PROFILE, WIN64_FILE_PROFILE,
    WIN64_SCRATCH_FILE_PROFILE, WIN64_PROCESS_PROFILE,
)

def bind_session_imports(data, image, opt, segments, bindings):
    allowed = {symbol for profile in WIN64_SESSION_PROFILES for symbol in profile['Imports']}
    if not bindings.keys() <= allowed:
        unknown = min(bindings.keys() - allowed)
        raise Rejection('PE-SESSION-TARGET', opt + 16, f'KERNEL32.dll!{unknown}')
    bind_fixed_imports(data, image, opt, segments, 'KERNEL32.dll', bindings, segments[:1])


def bind_fixed_imports(data, image, opt, segments, library, bindings, targets):
    directory = image['Directories'].get('imports')
    iat = image['Directories'].get('iat')
    if directory is None or iat is None:
        raise Rejection('PE-SESSION-IMPORT', opt + 120, 'DataDirectory.imports/iat')
    libraries = inventory_imports(data, image['Sections'], directory, opt + 120, include_slots=True)
    if len(libraries) != 1 or libraries[0]['DLL'].lower() != library.lower():
        raise Rejection('PE-SESSION-IMPORT', opt + 120, 'DataDirectory.imports')
    symbols = libraries[0]['Symbols']
    names = [symbol.get('Name') for symbol in symbols]
    if not names or len(set(names)) != len(names) or set(names) != set(bindings):
        missing = next((name or 'ordinal' for name in names if name not in bindings), 'ImportLookup')
        raise Rejection('PE-SESSION-IMPORT', opt + 120, f'{library}!{missing}')
    readonly = segments[1]
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
        if not any(perms == 5 and address <= target < address + len(code)
                   for address, code, _, perms in targets):
            raise Rejection('PE-SESSION-TARGET', opt + 16, f'{library}!{name}')
        struct.pack_into('<Q', payload, offset + index * 8, target)
    segments[1] = readonly[0], bytes(payload), readonly[2], readonly[3]
