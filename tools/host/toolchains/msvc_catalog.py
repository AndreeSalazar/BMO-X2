"""Compatibility inventory for the MSVC PE32+ x86-64 producer."""

from ..importers.pe import DIRECTORIES


STATES = {
    'qemu': 'Ejecucion demostrada en una prueba QEMU con un alcance concreto.',
    'host': 'Inspeccion o emision comprobable por HOST.',
    'pending': 'Requiere implementacion o evidencia adicional.',
}

# Rows describe the currently implemented profile, never an admission rule.
CATALOG = {
    'build': ('Compilacion y procedencia', (
        ('cl-link', 'cl.exe y link.exe x64', 'qemu', 'Cliente C freestanding empaquetado y ejecutado en CPL3.', 'host-msvc-qemu'),
        ('coff', 'Objetos COFF .obj', 'pending', 'Los bancos enlazan mediante link.exe. Falta un importador COFF general.'),
        ('archive', 'Bibliotecas estaticas .lib', 'pending', 'El enlace de archivos .lib corresponde al toolchain. HOST recibe la imagen final.'),
        ('manifest', 'Manifiesto y SHA-256', 'host', 'msvc.ps1 coteja el SHA-256 declarado con el PE.'),
        ('attestation', 'Atestacion del compilador y enlazador', 'pending', 'La etiqueta msvc y el manifiesto son declaraciones del build.'),
        ('pdb', 'PDB y depuracion simbolica', 'pending', 'La admision acotada de metadatos PE no incorpora un lector PDB.'),
    )),
    'image': ('Formato, memoria e ISA', (
        ('pe32plus', 'PE32+ AMD64', 'host', 'probe inventaria cabecera, tipo, entrada, secciones y directorios.'),
        ('fixed-exe', 'EXE freestanding fijo', 'qemu', 'Perfil acotado con entrada propia y sin CRT externo.', 'host-msvc-qemu'),
        ('console-subsystem', 'Subsistema consola', 'host', 'Los perfiles EXE admitidos verifican el valor de subsistema consola.'),
        ('entry', 'Punto de entrada', 'host', 'El RVA de entrada debe estar en bytes ejecutables mapeados.'),
        ('section-permissions', 'Secciones RX, R y RW', 'qemu', 'Los bancos comprueban permisos separados y rechazan W+X.', 'abi-msvc-sections-qemu'),
        ('zero-fill', 'BSS y relleno a cero', 'qemu', 'El cliente comprueba estado inicial cero y escrituras en datos.', 'abi-msvc-sections-qemu'),
        ('dir64', 'Reubicacion interna DIR64', 'qemu', 'Reubica punteros internos y ejecuta un EXE MSVC de cuatro regiones.', 'host-msvc-rebase-qemu'),
        ('aslr', 'ASLR de proceso completo', 'pending', 'La reubicacion interna de HOST prepara una base de carga fija para el perfil.'),
        ('isa', 'Declaracion x86-64-v1 a v4', 'host', 'SBEF v2 codifica el minimo ISA declarado. No se infiere por desensamblado.'),
    )),
    'directories': ('Directorios PE y politica de admision', tuple(
        (name, name, 'host', f'probe registra RVA y tamano. Bloqueo base {code}.' if index not in (3, 5, 6)
         else 'probe registra RVA y tamano. El empaquetador evalua las restricciones del perfil.')
        for index, (name, code) in DIRECTORIES.items()
    )),
    'imports': ('Imports y DLL', (
        ('import-inventory', 'Imports por nombre y ordinal', 'host', 'El inventario normal describe ambas formas. Los perfiles enlazan nombres admitidos.'),
        ('console-imports', 'KERNEL32.dll de consola', 'qemu', 'win64-console-v1 liga GetTickCount64, GetStdHandle y WriteFile al runtime Rust.', 'host-msvc-console-qemu'),
        ('iat-readonly', 'IAT resuelta de solo lectura', 'qemu', 'HOST liga destinos RX verificados antes de la carga externa.', 'host-msvc-console-qemu'),
        ('fixed-dll', 'Una DLL fija y una exportacion directa', 'qemu', 'pack --with-dll liga un EXE con una DLL sin entrada.', 'host-msvc-dll-qemu'),
        ('dll-lifecycle', 'DllMain y cierre de DLL', 'qemu', 'pack --with-dll-lifecycle prueba adjuntar, rechazar y cerrar el modulo.', 'host-msvc-dll-lifecycle-qemu'),
        ('dll-graph', 'Dependencias transitivas y reenvios', 'pending', 'El perfil fijo admite una DLL y exportaciones de codigo concretas.'),
        ('dynamic-load', 'LoadLibrary, GetProcAddress y FreeLibrary', 'pending', 'Falta un cargador dinamico de modulos en Ring 3.'),
        ('delay-load', 'Imports diferidos, vinculados y API sets', 'pending', 'Los perfiles vigentes resuelven imports normales con un contrato acotado.'),
    )),
    'runtime': ('Arranque C/C++, CRT y STL', (
        ('abi', 'Convencion Microsoft x64', 'qemu', 'El portal Win64 prueba INVOKE, WAIT y limpieza al salir en CPL3.', 'host-msvc-qemu'),
        ('startup', 'Entrada propia /ENTRY', 'qemu', 'El banco selecciona una entrada ligada al ABI de BMO-X2.', 'host-msvc-qemu'),
        ('constructors', 'Constructores C++ de MSVC', 'qemu', 'El banco recorre los inicializadores del cliente sin CRT externo.', 'host-msvc-dll-lifecycle-qemu'),
        ('atexit', 'atexit en orden inverso', 'qemu', 'El runtime del banco ejecuta los callbacks en el cierre.', 'host-msvc-dll-lifecycle-qemu'),
        ('crt-static', 'CRT estatico /MT', 'pending', 'Falta acreditar el arranque y los servicios que usa el CRT estatico.'),
        ('crt-dynamic', 'CRT dinamico /MD', 'pending', 'Faltan contratos para UCRT, VCRuntime y sus dependencias.'),
        ('ucrt', 'UCRT de proposito general', 'pending', 'Faltan stdio, locale, entorno y gestion completa de procesos.'),
        ('vcruntime', 'VCRuntime de proposito general', 'pending', 'Faltan los helpers de arranque, seguridad y excepciones.'),
        ('msvcp', 'Biblioteca estandar C++ y MSVCP', 'pending', 'Los usos acotados de C++ no acreditan compatibilidad STL general.'),
        ('rtti', 'RTTI, dynamic_cast y typeid', 'pending', 'Falta un contrato C++ compatible y evidencia de ejecucion.'),
        ('security-cookie', 'Cookies de seguridad /GS', 'pending', 'Los fixtures freestanding usan opciones acotadas de compilacion.'),
    )),
    'tls-exceptions': ('TLS, hilos y excepciones', (
        ('static-tls', 'Plantilla TLS estatica', 'qemu', 'pack --static-tls prepara la plantilla y su relleno cero.', 'host-msvc-tls-qemu'),
        ('thread-local', 'thread_local en dos hilos', 'qemu', 'Prueba secuencial con pilas y bases GS separadas.', 'host-msvc-tls-qemu'),
        ('tls-callback', 'Callbacks TLS', 'pending', 'El perfil de TLS estatico rechaza callbacks.'),
        ('dynamic-tls', 'TlsAlloc y ciclo de vida TLS general', 'pending', 'Faltan TLS dinamico y coordinacion con el planificador.'),
        ('unwind-metadata', '.pdata y UNWIND_INFO', 'host', 'El perfil fijo revisa metadatos acotados; no admite cadenas ni handlers.'),
        ('unwind-runtime', 'Desenrollado Win64 durante ejecucion', 'pending', 'La inspeccion de metadatos no ejecuta el desenrollador.'),
        ('seh', 'Structured Exception Handling', 'pending', 'Faltan despacho, busqueda y ejecucion de handlers compatibles.'),
        ('cpp-eh', 'Excepciones C++ /EHsc', 'pending', 'Faltan handlers C++ y destruccion de objetos durante unwind.'),
        ('cfg', 'Control Flow Guard y load config', 'pending', 'El empaquetado base bloquea el directorio load_config.'),
    )),
    'system': ('Servicios de sistema y graficos', (
        ('clock', 'Reloj, espera, stdout y salida', 'qemu', 'El cliente de consola usa servicios de sesion mediante SYSCALL.', 'host-msvc-console-qemu'),
        ('process', 'Procesos, argumentos y entorno Win32', 'pending', 'Solo hay contratos de sesion propios de BMO-X2.'),
        ('memory', 'VirtualAlloc, heap Win32 y mapeos', 'pending', 'Los mapas SBEF comprobados no exponen un administrador Win32 general.'),
        ('files', 'Archivos, registro y red Win32', 'pending', 'Faltan perfiles para estos servicios.'),
        ('sync', 'Hilos, locks y eventos Win32', 'pending', 'La sonda de hilos secuenciales no demuestra el modelo Win32 completo.'),
        ('native-panel', 'Panel MSVC en el escritorio nativo', 'qemu', 'El panel usa el contrato de UI de BMO-X2 y presenta pixeles en el fixture.', 'abi-msvc-rmlui-qemu'),
        ('user32', 'USER32, GDI y mensajes', 'pending', 'El panel nativo usa servicios de BMO-X2.'),
        ('com', 'COM, OLE y WinRT', 'pending', 'Faltan activacion, interfaz y ciclo de vida compatibles.'),
        ('directx', 'DXGI, Direct3D y DirectX', 'pending', 'Faltan contratos graficos y backend de ejecucion para estos binarios.'),
        ('vulkan', 'Vulkan de Windows', 'pending', 'Falta el cargador y el backend invitado para una aplicacion Windows.'),
    )),
}
def msvc_catalog(category=None):
    groups = []
    for key, (name, rows) in CATALOG.items():
        if category is not None and key != category:
            continue
        entries = []
        for item_id, title, state, boundary, *evidence in rows:
            item = dict(Id=item_id, Name=title, State=state, Boundary=boundary)
            if evidence:
                item['Evidence'] = f'Reports/{evidence[0]}.json'
            entries.append(item)
        groups.append(dict(Id=key, Name=name, Capabilities=entries))
    return groups
