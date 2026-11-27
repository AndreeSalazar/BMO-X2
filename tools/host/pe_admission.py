"""Explain default PE admission using the input inventory and fixture profiles."""

from html import escape

from .importers.pe_bindings import WIN64_SESSION_PROFILES


AREAS = (
    ('Arranque y entorno', 'Proveer argumentos, entorno, identidad y ciclo de vida del proceso.',
     'GetCommandLineA GetCommandLineW GetStartupInfoW ExitProcess TerminateProcess GetCurrentProcess '
     'GetCurrentProcessId GetCurrentThreadId GetEnvironmentStringsW FreeEnvironmentStringsW SetEnvironmentVariableW'),
    ('Archivos y consola', 'Implementar handles, acceso, posicion, errores, escritura y dispositivos de consola.',
     'CreateFileW ReadFile WriteFile CloseHandle GetLastError SetLastError SetFilePointerEx GetFileSizeEx '
     'SetEndOfFile FlushFileBuffers GetFileType DeleteFileW FindFirstFileExW FindNextFileW FindClose '
     'GetStdHandle SetStdHandle GetConsoleMode GetConsoleOutputCP ReadConsoleW WriteConsoleW'),
    ('Memoria', 'Dar al CRT un heap con los limites y errores esperados y aplicar permisos a sus paginas.',
     'GetProcessHeap HeapAlloc HeapReAlloc HeapFree HeapSize VirtualProtect'),
    ('TLS y sincronizacion', 'Mantener estado por hilo o fibra y contratos de sincronizacion del CRT.',
     'TlsAlloc TlsFree TlsGetValue TlsSetValue FlsAlloc FlsFree FlsGetValue FlsSetValue InitializeSListHead '
     'InitializeCriticalSectionAndSpinCount InitializeCriticalSectionEx EnterCriticalSection '
     'LeaveCriticalSection DeleteCriticalSection'),
    ('Cargador de modulos', 'Resolver modulos, exportaciones e identidad de imagen en el proceso.',
     'GetModuleFileNameW GetModuleHandleW GetModuleHandleExW GetProcAddress LoadLibraryExW FreeLibrary'),
    ('Excepciones y contexto', 'Conectar excepciones, marcos unwind y filtros al contexto del proceso.',
     'RaiseException RtlCaptureContext RtlLookupFunctionEntry RtlPcToFileHeader RtlUnwindEx RtlVirtualUnwind '
     'SetUnhandledExceptionFilter UnhandledExceptionFilter'),
    ('Texto y pagina de codigos', 'Proveer conversiones y reglas de texto de Windows que espera el CRT.',
     'GetACP GetOEMCP GetCPInfo IsValidCodePage MultiByteToWideChar WideCharToMultiByte CompareStringW '
     'GetStringTypeW LCMapStringW'),
    ('Tiempo y plataforma', 'Proveer reloj, capacidades de CPU y estado del proceso.',
     'GetTickCount64 QueryPerformanceCounter GetSystemTimeAsFileTime EncodePointer IsDebuggerPresent '
     'IsProcessorFeaturePresent'),
)
AREA_BY_SYMBOL = {name: title for title, _, names in AREAS for name in names.split()}
AREA_REASONS = {title: reason for title, reason, _ in AREAS}
AREA_REASONS['Otras dependencias'] = 'Identificar el contrato del simbolo o exportacion y probarlo en su modulo.'

BLOCKERS = {
    'PE-IMPORTS': ('El perfil PE base no resuelve dependencias Win64 para esta imagen.',
                   'Resolver cada DLL y simbolo con un perfil de proceso probado.'),
    'PE-IAT': ('Las ranuras importadas no tienen destinos ejecutables validados para esta imagen.',
               'Resolver las importaciones, validar cada ranura y publicar la IAT de solo lectura.'),
    'PE-LOAD-CONFIG': ('El perfil PE base no aplica la configuracion de seguridad declarada.',
                       'Validar y aplicar las protecciones requeridas antes de ejecutar el punto de entrada.'),
    'PE-TLS': ('La imagen declara almacenamiento TLS que el perfil PE base no materializa.',
               'Validar la plantilla, indices y callbacks y dar a cada hilo su bloque TLS.'),
    'PE-DELAY-IMPORTS': ('La imagen pide resolver dependencias al ejecutar.',
                         'Proveer un cargador que resuelva y valide importaciones diferidas.'),
    'PE-BOUND-IMPORTS': ('La imagen conserva enlaces de otra instancia del cargador.',
                         'Validar el enlace previo o resolver sus dependencias para este proceso.'),
    'PE-RESOURCES': ('La imagen declara recursos que el perfil PE base no admite.',
                     'Validar el directorio y exponer los recursos mediante el perfil correspondiente.'),
    'PE-SECURITY': ('La imagen incluye una tabla de certificados fuera del perfil PE base.',
                    'Definir el tratamiento de firma y preservar la procedencia de la imagen.'),
    'PE-CLR': ('La imagen requiere CLR y el perfil base ejecuta codigo nativo.',
               'Proveer un perfil que admita este ejecutable administrado.'),
}


def import_requirements(inventory):
    if 'ImportInventoryError' in inventory:
        return dict(Status='invalid', Error=inventory['ImportInventoryError'])
    areas = {}
    counts = dict(available_in_fixture=0, missing=0, ordinal=0)
    for library in inventory.get('Imports', []):
        dll = library['DLL']
        for symbol in library['Symbols']:
            name = symbol.get('Name')
            fixtures = [
                dict(Profile=profile['Name'], Target=profile['Imports'][name])
                for profile in WIN64_SESSION_PROFILES
                if dll.lower() == profile['DLL'].lower() and name in profile['Imports']
            ]
            area = (AREA_BY_SYMBOL.get(name, 'Otras dependencias') if dll.lower() == 'kernel32.dll'
                    else 'Otras dependencias')
            status = 'available_in_fixture' if fixtures else 'ordinal' if name is None else 'missing'
            counts[status] += 1
            item = dict(DLL=dll, **symbol, Status=status)
            if fixtures:
                item['Fixtures'] = fixtures
                item['Why'] = 'Existe un destino para un perfil de prueba, sin enlace automatico para esta imagen.'
                item['Required'] = 'Integrar y verificar el destino en el perfil de esta imagen.'
            elif status == 'ordinal':
                item['Why'] = 'El PE importa por numero y los perfiles de sesion enlazan por nombre.'
                item['Required'] = 'Identificar la exportacion ordinal en el modulo y resolverla de forma comprobada.'
            else:
                item['Why'] = 'Ningun perfil de sesion catalogado declara un destino para este simbolo.'
            areas.setdefault(area, []).append(item)
    return dict(Status='inventoried', Counts=counts, Groups=[
        dict(Name=area, Required=reason, Imports=areas[area],
             Pending=sum(item['Status'] != 'available_in_fixture' for item in areas[area]))
        for area, reason in AREA_REASONS.items() if area in areas
    ])


def explain_pe(inventory):
    findings = []
    for blocker in inventory['Blockers']:
        code = blocker['Code']
        why, required = BLOCKERS.get(code, (
            'El campo indicado queda fuera de las reglas del perfil PE base.',
            'Revisar el campo y el desplazamiento antes de extender la admision.',
        ))
        finding = dict(blocker, Why=why, Required=required)
        if code == 'PE-LOAD-CONFIG':
            config = inventory.get('LoadConfigInventory')
            if config:
                if config['SecurityCookieVA']:
                    finding['Required'] += ' Inicializar la cookie de seguridad en su ubicacion validada.'
                if config['GuardFlags'] or config['GuardCFDispatchFunctionPointerVA']:
                    finding['Required'] += ' Resolver la politica CFG y sus destinos de chequeo y despacho.'
                finding['Observed'] = config
            elif 'LoadConfigInventoryError' in inventory:
                finding['Observed'] = inventory['LoadConfigInventoryError']
        elif code == 'PE-IAT':
            finding['Observed'] = inventory.get('Directories', {}).get('iat')
        elif code == 'PE-IMPORTS' and 'ImportInventoryError' in inventory:
            finding['Why'] = 'El HOST no pudo inventariar la tabla de importaciones.'
            finding['Required'] = 'Corregir primero la estructura PE que indica el error de inventario.'
            finding['Observed'] = inventory['ImportInventoryError']
        findings.append(finding)
    return dict(
        Profile='pe-base', Status='eligible' if inventory['CanPack'] else 'blocked',
        Scope='Diagnostico de admision del PE. La evidencia de cada destino se limita a su perfil de prueba.',
        Blockers=findings, Imports=import_requirements(inventory),
    )


def markdown_admission(admission):
    lines = ['# Admision PE en HOST', '', f'**Estado** {admission["Status"]}', '', admission['Scope']]
    for item in admission['Blockers']:
        lines.extend(('', f'## {item["Code"]}', '', f'{item["Field"]} en 0x{item["Offset"]:X}.',
                      item['Why'], item['Required']))
        observed = item.get('Observed')
        if observed:
            lines += ['', *(f'- **{key}** {escape(str(value))}' for key, value in observed.items())]
    imports = admission['Imports']
    if imports['Status'] == 'invalid':
        error = imports['Error']
        lines.extend(('', f'**Inventario invalido** {error["Code"]} en 0x{error["Offset"]:X}.'))
        return '\n'.join(lines)
    counts = imports['Counts']
    lines.extend(('', '## Importaciones', '',
                  f'{counts["available_in_fixture"]} con evidencia acotada, {counts["missing"]} pendientes '
                  f'y {counts["ordinal"]} ordinales por resolver.'))
    labels = {'available_in_fixture': 'Perfil de prueba', 'missing': 'Pendiente', 'ordinal': 'Ordinal pendiente'}
    for group in imports['Groups']:
        lines.extend(('', f'### {group["Name"]} ({group["Pending"]} pendientes)', '', group['Required'], ''))
        for item in group['Imports']:
            name = item.get('Name', f'#{item.get("Ordinal")}')
            symbol = escape(f'{item["DLL"]}!{name}').replace('`', '&#96;')
            profiles = ', '.join(fixture['Profile'] for fixture in item.get('Fixtures', []))
            detail = f' ({profiles})' if profiles else ''
            lines.append(f'- `{symbol}` {labels[item["Status"]]}{detail}')
    return '\n'.join(lines)
