"""Classify Windows x64 dependencies reported by the PE reader."""

from ..importers.pe_bindings import WIN64_CONSOLE_PROFILE


# These levels describe the implementation scope of a dependency family.
# API-set prefixes recognize contract names without resolving their host DLLs.
LEVELS = {
    'base': (
        ('core', 'Proceso, memoria y consola',
         'kernel32 kernelbase ntdll', 'api-ms-win-core-'),
        ('crt', 'CRT de C y runtime de C++',
         'ucrtbase ucrtbased msvcrt vcruntime140 vcruntime140_1 vcruntime140_threads '
         'vcruntime140d vcruntime140_1d msvcp140 msvcp140_1 msvcp140_2 '
         'msvcp140_atomic_wait msvcp140_codecvt_ids msvcp140d concrt140 vcomp140',
         'api-ms-win-crt-'),
        ('system-config', 'Seguridad, registro y configuracion',
         'advapi32 sechost psapi version cfgmgr32 setupapi userenv profapi', ''),
    ),
    'intermedio': (
        ('desktop', 'Ventanas, entrada y dibujo 2D',
         'user32 gdi32 gdi32full win32u comctl32 comdlg32 imm32 uxtheme '
         'msimg32 shcore shell32 shlwapi dwmapi hid xinput1_4',
         'api-ms-win-ntuser- ext-ms-win-ntuser-'),
        ('com', 'COM, automatizacion y RPC',
         'ole32 oleaut32 combase rpcrt4 propsys actxprxy', ''),
        ('network', 'Red, HTTP y resolucion de nombres',
         'ws2_32 mswsock dnsapi iphlpapi winhttp wininet urlmon netapi32 dhcpcsvc', ''),
        ('crypto', 'Criptografia y certificados',
         'bcrypt ncrypt crypt32 cryptui cryptnet secur32 sspicli wintrust wldap32', ''),
        ('storage', 'Volumenes, montaje y compresion',
         'virtdisk vssapi cldapi wofutil cabinet', ''),
    ),
    'avanzado': (
        ('graphics', 'Direct3D, DXGI, Vulkan y OpenGL',
         'dxgi d3d9 d3d10 d3d10_1 d3d11 d3d12 d3d12core d3dcompiler_47 dxcompiler '
         'dxil d2d1 dwrite dwritecore windowscodecs dcomp opengl32 vulkan-1', ''),
        ('media', 'Audio, video y captura',
         'winmm mmdevapi avrt xaudio2_9 xapofx1_5 dsound mf mfplat mfreadwrite '
         'ksuser avicap32', ''),
        ('winrt', 'WinRT y XAML',
         'windows.storage runtimeobject windows.applicationmodel '
         'windows.ui windows.ui.xaml microsoft.ui.xaml', ''),
        ('diagnostics', 'Diagnostico, depuracion y rendimiento',
         'dbghelp dbgcore imagehlp tdh wevtapi wer pdh', ''),
        ('system-devices', 'Administracion y dispositivos',
         'powrprof wecapi winusb wtsapi32 wbemprox bluetoothapis', ''),
    ),
}

DLL_GROUPS = {
    dll + '.dll': (level, group)
    for level, groups in LEVELS.items()
    for group, _, names, _ in groups
    for dll in names.split()
}
CONTRACT_GROUPS = tuple(
    (prefix, level, group)
    for level, groups in LEVELS.items()
    for group, _, _, prefixes in groups
    for prefix in prefixes.split()
)


def windows_catalog(level=None):
    return [
        dict(Level=name, Groups=[
            dict(Id=group, Name=title, DLLs=[dll + '.dll' for dll in names.split()],
                 ContractPrefixes=prefixes.split())
            for group, title, names, prefixes in groups
        ])
        for name, groups in LEVELS.items() if level in (None, 'todos', name)
    ]


def dependency_family(dll):
    dll = dll.lower()
    level, group = DLL_GROUPS.get(dll, (None, None))
    if group is None and dll.endswith('.dll'):
        for prefix, contract_level, contract_group in CONTRACT_GROUPS:
            if dll.startswith(prefix):
                return contract_level, contract_group
    return level, group


def import_coverage(libraries):
    profile = WIN64_CONSOLE_PROFILE
    console_dll = profile['DLL'].lower()
    dependencies = []
    fixture_symbols = 0
    total_symbols = 0
    for library in libraries:
        dll = library['DLL'].lower()
        level, group = dependency_family(dll)
        bindings = profile['Imports'] if dll == console_dll else {}
        matches, pending = [], []
        for symbol in library['Symbols']:
            target = bindings.get(symbol.get('Name'))
            if target is None:
                pending.append(symbol)
            else:
                matches.append(dict(symbol, Target=target))
        fixture_symbols += len(matches)
        total_symbols += len(matches) + len(pending)
        dependencies.append(dict(DLL=library['DLL'], Level=level, Group=group,
                                 FixtureSymbols=matches, PendingSymbols=pending))
    return dict(
        Scope='Regular PE imports; fixture matches are diagnostic and do not bind or admit the PE.',
        FixtureProfile=profile['Name'], LibraryCount=len(dependencies), SymbolCount=total_symbols,
        FixtureSymbolCount=fixture_symbols, PendingSymbolCount=total_symbols - fixture_symbols,
        Libraries=dependencies,
    )
