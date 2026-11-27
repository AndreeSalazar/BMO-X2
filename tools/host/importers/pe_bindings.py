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
        'FindFirstFileExW': 'bmo_package_find_first',
        'FindNextFileW': 'bmo_package_find_next',
        'FindClose': 'bmo_package_find_close',
        'DeleteFileW': 'bmo_package_delete',
    },
    'Scope': 'External single-threaded QEMU fixture with a 4 KiB volatile output file',
}

WIN64_PROCESS_PROFILE = {
    **WIN64_CONSOLE_PROFILE,
    'Name': 'win64-process-start-v1',
    'Imports': {
        'GetStdHandle': 'bmo_get_std_handle',
        'SetStdHandle': 'bmo_set_std_handle',
        'GetConsoleMode': 'bmo_get_console_mode',
        'GetConsoleOutputCP': 'bmo_get_console_output_cp',
        'ReadConsoleW': 'bmo_read_console_w',
        'WriteConsoleW': 'bmo_write_console_w',
        'WriteFile': SESSION_EXPORTS['WriteFile'],
        'GetCommandLineW': 'bmo_get_command_line_w',
        'GetCommandLineA': 'bmo_get_command_line_a',
        'GetStartupInfoW': 'bmo_get_startup_info_w',
        'GetACP': 'bmo_get_acp',
        'GetOEMCP': 'bmo_get_oem_cp',
        'IsValidCodePage': 'bmo_is_valid_code_page',
        'GetCPInfo': 'bmo_get_cp_info',
        'MultiByteToWideChar': 'bmo_multi_byte_to_wide_char',
        'WideCharToMultiByte': 'bmo_wide_char_to_multi_byte',
        'GetLastError': 'bmo_get_last_error',
        'SetLastError': 'bmo_set_last_error',
        'ExitProcess': 'bmo_exit_process',
        'TlsAlloc': 'bmo_tls_alloc',
        'TlsFree': 'bmo_tls_free',
        'TlsGetValue': 'bmo_tls_get_value',
        'TlsSetValue': 'bmo_tls_set_value',
        'InitializeSListHead': 'bmo_initialize_slist_head',
        'FlsAlloc': 'bmo_fls_alloc',
        'FlsFree': 'bmo_fls_free',
        'FlsGetValue': 'bmo_fls_get_value',
        'FlsSetValue': 'bmo_fls_set_value',
        'GetCurrentThreadId': 'bmo_get_current_thread_id',
        'InitializeCriticalSectionEx': 'bmo_initialize_critical_section_ex',
        'InitializeCriticalSectionAndSpinCount': 'bmo_initialize_critical_section_and_spin_count',
        'EnterCriticalSection': 'bmo_enter_critical_section',
        'LeaveCriticalSection': 'bmo_leave_critical_section',
        'DeleteCriticalSection': 'bmo_delete_critical_section',
        'GetEnvironmentStringsW': 'bmo_get_environment_strings_w',
        'FreeEnvironmentStringsW': 'bmo_free_environment_strings_w',
        'SetEnvironmentVariableW': 'bmo_set_environment_variable_w',
        'GetCurrentProcess': 'bmo_get_current_process',
        'GetCurrentProcessId': 'bmo_get_current_process_id',
        'TerminateProcess': 'bmo_terminate_process',
        'QueryPerformanceCounter': 'bmo_query_performance_counter',
        'QueryPerformanceFrequency': 'bmo_query_performance_frequency',
        'IsProcessorFeaturePresent': 'bmo_is_processor_feature_present',
        'IsDebuggerPresent': 'bmo_is_debugger_present',
        'GetModuleFileNameW': 'bmo_get_module_file_name_w',
        'GetModuleHandleW': 'bmo_get_module_handle_w',
        'GetModuleHandleExW': 'bmo_get_module_handle_ex_w',
        'GetProcAddress': 'bmo_get_proc_address',
        'LoadLibraryExW': 'bmo_load_library_ex_w',
        'FreeLibrary': 'bmo_free_library',
        'RtlCaptureContext': 'bmo_rtl_capture_context',
        'RtlPcToFileHeader': 'bmo_rtl_pc_to_file_header',
        'RtlLookupFunctionEntry': 'bmo_rtl_lookup_function_entry',
        'SetUnhandledExceptionFilter': 'bmo_set_unhandled_exception_filter',
        'UnhandledExceptionFilter': 'bmo_unhandled_exception_filter',
    },
    'Scope': 'Single-threaded QEMU startup with UTF-16, UTF-8 ACP, DWORD exit and dynamic TLS/FLS',
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
