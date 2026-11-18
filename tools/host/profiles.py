"""Registro machine-readable de productores, formatos y perfiles x86-64."""

from .sbef.isa import PROFILES as ISA_PROFILES

HOST_TARGET = 'x86-64'
ISA_POLICY = {
    'Baseline': 'x86-64-v1',
    'BaselineFrozen': True,
    'FeatureListsAreAdditions': True,
    'Levels': ISA_PROFILES,
    'SBEFFormatVersion': 2,
    'LegacySBEF': 'Format v1 has flags=0 and means x86-64-v1.',
    'RuntimeDetection': 'Ring 0 checks CPUID, CR4.OSFXSR, and XCR0 where required before entry.',
    'DeclarationSemantics': 'The SBEF field declares the minimum ISA profile; HOST does not disassemble or prove that every instruction obeys the declaration.',
    'ProbeStatus': 'The checker is wired into two LLVM assembly QEMU staging loaders; build/QEMU evidence is pending, and generic CASM enforcement remains pending.',
    'ExtensionsOutsideLevels': 'Vendor-specific and unlisted extensions are not declared by this profile table.',
}

CAPABILITY_CATALOG = [
    {
        'Id': 'producer-msvc',
        'Family': 'producer',
        'State': 'fixture-specific',
        'Implementation': ['tools/host/toolchains/msvc.py', 'tools/host/msvc.ps1'],
        'Boundary': 'El intake recibe PE32+ x86-64; el productor declarado no se infiere ni se atesta desde sus bytes.',
    },
    {
        'Id': 'format-pe32plus',
        'Family': 'container',
        'State': 'partial',
        'Implementation': ['tools/host/importers/pe.py'],
        'Boundary': 'Inspeccion general PE y admision freestanding limitada; no equivale a cargar cualquier EXE o DLL.',
    },
    {
        'Id': 'object-coff-x64',
        'Family': 'object',
        'State': 'fixture-only',
        'Implementation': ['tools/host/toolchains/msvc.py'],
        'Boundary': 'Hay fixtures enlazados por MSVC y extraccion acotada de una funcion confiable; no existe importador general de objetos COFF.',
    },
    {
        'Id': 'format-elf64-static',
        'Family': 'container',
        'State': 'profile-limited',
        'Implementation': ['tools/host/importers/elf.py'],
        'Boundary': 'Admite ELF64 x86-64 estatico bajo el perfil; no acredita los runtimes del productor.',
    },
    {
        'Id': 'isa-x86-64',
        'Family': 'instruction-set',
        'State': 'partial',
        'Implementation': ['tools/host/sbef/isa.py', 'tools/host/sbef/format.py',
                           'kernel/arch/x86_64/cpu/isa_profile_check.inc'],
        'Boundary': 'SBEF v2 declara x86-64-v1..v4 y el codigo del chequeo CPU/estado esta integrado en dos cargadores LLVM de staging; falta evidencia de build/QEMU y la integracion CASM del cargador general.',
    },
    {
        'Id': 'relocation-pe-dir64',
        'Family': 'relocation',
        'State': 'partial',
        'Implementation': ['tools/host/importers/pe.py'],
        'Boundary': 'DIR64 interna validada dentro de regiones mapeadas; no hay relocacion PE general.',
    },
    {
        'Id': 'imports-and-runtime',
        'Family': 'abi-runtime',
        'State': 'selected-services-only',
        'Implementation': ['tools/host/importers/pe_imports.py', 'tools/host/importers/pe_bindings.py'],
        'Boundary': 'Catalogo acotado de servicios para fixtures; UCRT, VCRuntime, Win32 general y DLL siguen pendientes.',
    },
    {
        'Id': 'sbef-external-process',
        'Family': 'execution',
        'State': 'fixture-specific',
        'Implementation': ['tools/host/sbef/format.py', 'kernel/loader/doom_engine_loader.S'],
        'Boundary': 'Hay recorridos QEMU concretos; el cargador generico de procesos SBEF externos en Ring 3 no esta demostrado.',
    },
]

LAYERS = [
    {
        'Id': 'producer',
        'Name': 'Productor y procedencia',
        'Responsibility': 'Define evidencia del compilador, enlazador, versiones, opciones y huellas de entrada.',
        'Status': 'El intake acepta un manifiesto manual ligado al hash; la generacion y verificacion automatica siguen pendientes.',
        'Boundary': 'El lenguaje y el compilador no demuestran compatibilidad de runtime.',
    },
    {
        'Id': 'artifact-format',
        'Name': 'Formato de objeto y ejecutable',
        'Responsibility': 'Selecciona un lector acotado de imagen PE32+ o ELF64 estatico.',
        'Status': 'Existen lectores PE32+ y ELF64; no hay intake general de objetos COFF.',
        'Boundary': 'El lector PE se comparte entre productores PE32+; el enlace de objetos depende del toolchain.',
    },
    {
        'Id': 'target-profile',
        'Name': 'Perfil de admision x86-64',
        'Responsibility': 'Comprueba maquina, secciones, relocaciones, imports, permisos y limites.',
        'Status': 'Hay reglas parciales por perfil; no se asume compatibilidad general.',
        'Boundary': 'Cada perfil admite solo funciones con semantica definida en BMO-X2.',
    },
    {
        'Id': 'sbef-package',
        'Name': 'Emision y lectura SBEF',
        'Responsibility': 'Emite SBEF y vuelve a validar sus bytes antes de publicarlo.',
        'Status': 'El lector HOST existe; la carga invitada se acredita por separado.',
        'Boundary': 'Empaquetar no demuestra que el cargador invitado pueda ejecutarlo.',
    },
    {
        'Id': 'guest-execution',
        'Name': 'Cargador y runtime Ring 3',
        'Responsibility': 'Mapea el proceso y ofrece solo los servicios declarados.',
        'Status': 'La carga externa general y el runtime amplio siguen pendientes.',
        'Boundary': 'Esta funcion pertenece al invitado; no la ofrece el empaquetador HOST.',
    },
    {
        'Id': 'ring0-boundary',
        'Name': 'Frontera NANO-CORE',
        'Responsibility': 'Valida SBEF/ABI y media las capacidades declaradas.',
        'Status': 'El contrato es acotado; los runtimes viven en Ring 3.',
        'Boundary': 'Win32, CRT, LLVM y detalles de compilador no entran a Ring 0.',
    },
]

PROFILES = [
    {
        'Id': 'msvc-x86_64-pe32plus',
        'Producer': 'MSVC cl.exe + link.exe',
        'ObjectFormat': 'COFF x86-64',
        'ExecutableFormat': 'PE32+',
        'Target': HOST_TARGET,
        'Admission': 'partial',
        'AdmissionEvidence': 'Intake PE, perfiles freestanding acotados y empaquetado de relocacion DIR64 interna.',
        'Execution': 'fixture-specific',
        'ExecutionEvidence': 'Las pruebas ABI y de servicios declarados tienen evidencia QEMU. El paquete generico de cuatro regiones aun no tiene evidencia de carga generica en QEMU.',
        'Provenance': 'Manifiesto opcional del usuario; HOST valida que el hash PE coincida, pero no verifica la identidad del compilador ni del enlazador.',
        'SharedImplementation': [
            'tools/host/msvc.ps1',
            'tools/host/toolchains/msvc.py',
            'tools/host/importers/pe.py',
            'tools/host/importers/pe_imports.py',
            'tools/host/importers/pe_bindings.py',
            'tools/host/sbef/format.py',
        ],
        'KnownGaps': ['generacion y atestacion independiente del manifiesto de build', 'importacion de objetos COFF y flujo de enlace propio', 'imports generales y carga de DLL', 'TLS', 'configuracion de carga y CFG', 'unwind y excepciones generales', 'servicios generales UCRT/VCRuntime/MSVCP y Win32'],
    },
    {
        'Id': 'llvm-clang-x86_64-elf64-static',
        'Producer': 'LLVM Clang + LLD, x86_64-unknown-none-elf',
        'ObjectFormat': 'ELF64 x86-64',
        'ExecutableFormat': 'static ELF64 ET_EXEC',
        'Target': HOST_TARGET,
        'Admission': 'format-profile-implemented',
        'AdmissionEvidence': 'El lector ELF compartido admite layouts estaticos PT_LOAD acotados y emite SBEF; no infiere el productor a partir de ELF.',
        'Execution': 'generic-external-load-not-established',
        'ExecutionEvidence': 'Existen pruebas concretas de compilador y ABI; no demuestran ejecucion general de programas ELF empaquetados externamente.',
        'SharedImplementation': ['tools/host/importers/elf.py', 'tools/host/sbef/format.py'],
        'KnownGaps': ['carga generica de procesos SBEF externos', 'servicios de runtime que requiere cada programa'],
    },
    {
        'Id': 'llvm-clang-cl-x86_64-pe32plus',
        'Producer': 'LLVM clang-cl + lld-link',
        'ObjectFormat': 'COFF x86-64',
        'ExecutableFormat': 'PE32+',
        'Target': HOST_TARGET,
        'Admission': 'format-reader-shared-producer-profile-unverified',
        'AdmissionEvidence': 'El lector PE compartido puede inspeccionar PE; este par productor/enlazador aun no esta certificado como perfil propio.',
        'Execution': 'not-established',
        'ExecutionEvidence': 'No hay una afirmacion de ejecucion QEMU especifica de este productor.',
        'SharedImplementation': ['tools/host/importers/pe.py', 'tools/host/sbef/format.py'],
        'KnownGaps': ['fixture de intake clang-cl/lld-link', 'registro de procedencia del productor', 'carga generica de procesos SBEF externos'],
    },
    {
        'Id': 'gcc-x86_64-elf64-static',
        'Producer': 'GCC + ELF linker',
        'ObjectFormat': 'ELF64 x86-64',
        'ExecutableFormat': 'static ELF64 ET_EXEC',
        'Target': HOST_TARGET,
        'Admission': 'producer-neutral-format-profile',
        'AdmissionEvidence': 'La salida GCC solo se admite si cumple el perfil ELF estatico compartido; el lector no infiere procedencia GCC.',
        'Execution': 'fixture-specific',
        'ExecutionEvidence': 'Una ruta concreta GCC/DOOM no acredita programas o bibliotecas GCC arbitrarios.',
        'SharedImplementation': ['tools/host/importers/elf.py', 'tools/host/sbef/format.py'],
        'KnownGaps': ['matriz de productores GCC por version', 'servicios de runtime que requiere cada programa', 'carga generica de procesos SBEF externos'],
    },
    {
        'Id': 'rustc-x86_64-elf64-static',
        'Producer': 'rustc, freestanding x86-64 target',
        'ObjectFormat': 'ELF64 x86-64',
        'ExecutableFormat': 'static ELF64 ET_EXEC',
        'Target': HOST_TARGET,
        'Admission': 'producer-neutral-format-profile',
        'AdmissionEvidence': 'Los artefactos Rust usan los contratos ELF/SBEF compartidos cuando cumplen el perfil estatico.',
        'Execution': 'fixture-specific',
        'ExecutionEvidence': 'El escritorio y las pruebas ABI en Rust tienen evidencia acotada; no demuestran un cargador general de procesos externos.',
        'SharedImplementation': ['tools/host/importers/elf.py', 'tools/host/sbef/format.py'],
        'KnownGaps': ['carga generica de procesos SBEF externos', 'servicios de runtime que requiere cada programa'],
    },
]

ADMISSION_POLICY = [
    {
        'Order': 1,
        'Id': 'external-sbef-process-loader',
        'Name': 'Cargador general de procesos SBEF externos',
        'State': 'partial',
        'CurrentLimit': 'La sonda QEMU acepta layouts fijos de una a tres regiones; falta integracion CASM, mapeo general y ciclo de vida por proceso.',
        'ExitCriteria': [
            'Ring 0 CASM recibe el SBEF externo y vuelve a validar cabecera, ABI, arquitectura, regiones, rangos, entrada y W^X antes de mapear.',
            'Carga los layouts SBEF admitidos de una a ocho regiones, inicializa BSS y pila, y entra a CPL3 con permisos efectivos.',
            'Salida y fallos revocan y limpian todas las paginas del proceso sin dejar mappings activos.',
            'QEMU prueba fixtures validos y mutaciones rechazadas; HOST y CASM coinciden en mapa, motivo y offset.',
        ],
    },
    {
        'Order': 2,
        'Id': 'x86-64-baseline-in-sbef',
        'Name': 'Perfil ISA x86-64 congelado y declarado en SBEF',
        'State': 'partial',
        'CurrentLimit': 'x86-64-v1 esta fijado como base; SBEF v2 codifica cuatro niveles y el codigo de dos cargadores LLVM de staging consulta CPUID/CR4/XCR0. Falta compilar y probar esas sondas; la comprobacion general CASM depende de cerrar primero la puerta 1. La declaracion SBEF no es una prueba por desensamblado.',
        'ExitCriteria': [
            'Mantener publicada la tabla x86-64-v1..v4 y el esquema versionado de requisitos SBEF; el formato v1 heredado implica x86-64-v1.',
            'Al cerrar la puerta 1, integrar en CASM el mismo chequeo CPUID/CR4/XCR0 antes de mapear o ejecutar.',
            'QEMU y fixtures prueban cada nivel admitido y rechazan de forma determinista CPU o estado insuficiente; HOST y CASM coinciden.',
            'Cada productor declara y demuestra su nivel mediante opciones de build registradas y fixtures; una etiqueta SBEF sola no acredita el contenido de instrucciones.',
        ],
    },
    {
        'Order': 3,
        'Id': 'freestanding-producer-fixtures',
        'Name': 'Fixtures freestanding por productor x86-64',
        'State': 'partial',
        'CurrentLimit': 'Hay recorridos concretos para MSVC, GCC y Rust, y lectores comunes ELF/PE; faltan fixtures y matriz propia para algunas parejas productor/enlazador.',
        'Producers': [
            'MSVC cl.exe + link.exe -> PE32+ / COFF x64',
            'LLVM Clang + LLD -> ELF64 estatico',
            'LLVM clang-cl + lld-link -> PE32+ / COFF x64',
            'GCC + enlazador ELF -> ELF64 estatico',
            'rustc freestanding -> ELF64 estatico',
        ],
        'ExitCriteria': [
            'Cada pareja tiene fuente minima sin imports, target, versiones, opciones y hashes de entrada/salida registrados automaticamente.',
            'HOST produce SBEF verificable y se ejecuta por el cargador general en QEMU; el caso no soportado produce diagnostico estable.',
            'La evidencia identifica productor y enlazador por separado de lo que HOST puede inferir del formato.',
        ],
    },
    {
        'Order': 4,
        'Id': 'bmo-abi-bridges',
        'Name': 'Puentes ABI hacia el ABI BMO-X2',
        'State': 'partial',
        'CurrentLimit': 'Existe un portal MSVC Win64 para fixtures; no hay una matriz congelada de puentes y reglas por productor.',
        'ExitCriteria': [
            'Especificar el ABI BMO-X2 y los bordes permitidos para Microsoft x64, SysV x86-64 y Rust/C/C++.',
            'Rust cruza la frontera por ABI BMO-X2 versionado o extern C; no se admite asumir estabilidad del ABI Rust nativo.',
            'Implementar thunks explicitos; no inferir que dos objetos comparten convencion por usar el mismo lenguaje o ISA.',
            'QEMU comprueba argumentos, retorno, alineacion de pila, registros preservados y errores para cada puente publicado.',
        ],
    },
    {
        'Order': 5,
        'Id': 'versioned-runtimes-and-imports',
        'Name': 'Runtimes e imports versionados',
        'State': 'partial',
        'CurrentLimit': 'Solo servicios seleccionados para fixtures; UCRT, VCRuntime, Win32 general, TLS, excepciones y DLL generales no estan completos.',
        'ExitCriteria': [
            'Cada import se resuelve contra un servicio versionado con contrato de memoria, error y capacidad.',
            'Agregar CRT, startup, TLS, unwind, excepciones, RTTI y bibliotecas por perfil; no sustituir funciones ausentes por stubs silenciosos.',
            'Imports, formatos, runtimes e instrucciones no admitidos se rechazan con codigo, campo, offset y productor/perfil.',
            'Cada ampliacion tiene casos positivos y negativos en QEMU y mide tamano, memoria y coste de ejecucion.',
        ],
    },
]

ADMISSION_ADVANCE_RULE = (
    'El orden de las puertas define el cierre de compatibilidad. Se puede preparar trabajo de etapas futuras, '
    'pero no declarar un productor general ni un runtime admitido hasta cumplir y registrar los criterios '
    'de todas las puertas anteriores. Una lectura de formato o un fixture no acredita ejecucion general.'
)


def profile_report():
    """Return the current x86-64 HOST layer and producer matrix."""
    return {
        'Schema': 1,
        'Target': HOST_TARGET,
        'InstructionSetPolicy': ISA_POLICY,
        'AdmissionPolicyVersion': 1,
        'AdmissionAdvanceRule': ADMISSION_ADVANCE_RULE,
        'AdmissionPolicy': ADMISSION_POLICY,
        'CapabilityCatalog': CAPABILITY_CATALOG,
        'ProducerIdentityRule': 'El intake MSVC acepta un manifiesto para PE32+ ligado al hash; la declaracion no prueba que esas herramientas hayan generado el archivo.',
        'StatusLegend': {
            'partial': 'Reglas acotadas implementadas; no implica compatibilidad general.',
            'format-profile-implemented': 'El lector admite el formato bajo un perfil; no acredita todas las salidas del productor.',
            'format-reader-shared-producer-profile-unverified': 'El lector de formato puede inspeccionar el archivo; falta validar el productor propio.',
            'producer-neutral-format-profile': 'Se valida el formato sin identificar el compilador que lo produjo.',
            'fixture-specific': 'Solo hay evidencia para las pruebas nombradas, no para cualquier programa.',
            'generic-external-load-not-established': 'No se ha demostrado la carga generica del paquete externo.',
            'not-established': 'No hay evidencia de ejecucion para este perfil.',
        },
        'Layers': LAYERS,
        'Profiles': PROFILES,
        'IsaProfiles': ISA_PROFILES,
        'OtherArchitectures': 'Fuera del alcance de BMO-X2; este proyecto sigue siendo exclusivo x86-64.',
    }
