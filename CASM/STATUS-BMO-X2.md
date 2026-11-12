# CASM en BMO-X2

Esta pagina manda sobre los estados heredados de los README de origen.
Esos documentos conservan la fecha, el entorno y el alcance de su trabajo.

| Perfil | Fuentes | Lo disponible | Lo que no acredita |
|---|---|---|---|
| metal64 0.2 | `src/`, `verify.py`, `test.py` | Semilla C11, enteros constantes exactos, HEX e IR, paquete FAGRAW64 comprobado. | Kernel completo, variables de ejecucion, MMIO o cambios de privilegio. |
| ring0-stop 0.1 | `src/kernel/stop.c`, `stop_verify.py` | Parada propia de 4 bytes; IR3 cerrada; siete casos QEMU en Ring 0. | Kernel completo, interrupciones generales, arranque autonomo o ahorro energetico medido. |
| ring0-cpu 0.1 | `src/kernel/stop.c`, `stop_verify.py` | Sonda CPUID hoja 0 de 8 bytes, IR4 y perfil observado en QEMU. | Aplicar configuracion de CPU, memoria o dispositivos. |
| ring0-context 0.1 | `src/kernel/stop.c`, `stop_verify.py` | Entrada de 50 bytes con IR5. QEMU observa la pila elegida y el rechazo de RDI nulo. | Tablas de memoria propias, pagina de guarda o manejo de excepciones. |
| ring0-splash 0.1 | `src/kernel/splash.c`, `splash_verify.py` | Gato animado, 484 bytes de cuerpo e IR6. QEMU comprueba tres cuadros. | Escritorio, arranque integrado o ejecucion fisica. |
| Native 0.1 | `native/` | Compilador CASM, funciones, bucles, buffers, guardas; autocompilacion documentada en Linux. | Autocompilacion nueva en Windows o dentro de BMO-X2. |
| Native freestanding | `native/freestanding.py` | Adaptador sin servicios Linux, con permisos y trampas declarados. | Imagen EFI ni kernel; sigue necesitando cargador y manejador #UD. |
| metal64 0.3 | `traspaso/` | Parche de investigacion con RDTSC y trampas. | Verificador completo: NO se ha aplicado al compilador de esta copia. |

## Primera base reproducible

Genesis G1 ya ejecuta una fuente CASM propia bajo QEMU/OVMF: cuerpo de 22
bytes, paquete de 46, salida y retorno verificados en Ring 0. Siete casos de
carga/arranque pasaron. El puente UEFI es HEX manual heredado de TALK-CPU;
CASM no lo genero. Esto no completa operaciones privilegiadas propias ni
arranque autonomo. Ver `../kernel/boot/genesis/evidence/qemu.json`.

Revision HOST del 05-11-2026: el frontend metal64 esta repartido en lexer,
simbolos, enteros y parser, con tipos y almacenamiento en `src/model/`.
`sources.json` alimenta las construcciones Windows y Linux e incluye las
cabeceras en la vigencia de la cache. [Fronteras del frontend](src/frontend/README.md).

`catalog.json` organiza 49 elementos jerarquicos. El build valida el catalogo
y genera la tabla de tipos desde el, contrastada con la tabla independiente
del verificador. SUPER GRAFO ahora lee la jerarquia y los modulos completos;
la consulta `casm` expone tipos, IR, codificaciones, reglas y bytes por linea.
Ver [CATALOG](CATALOG.md).

`bmo-x2.ps1 -Accion comprobar` construye metal64 con Clang del anfitrion y
corre el banco heredado. La adaptacion de `test.py` para Windows omite
explicitamente el caso de RLIMIT_DATA; no imita el limite ni lo cuenta aprobado.
En Linux se conserva ese caso. La generacion Native se vuelve a probar en su
taller Linux/QEMU; no se ejecutan ELF Linux en Windows.

`bmo-x2.ps1 -Accion compilar` congela fuente y herramientas, emite HEX e IR,
verifica y publica `INICIO.X86` solo si el verificador acepta. SUPER GRAFO
puede leer esa compilacion en `build/CASM/run-*` y mostrar linea -> bytes.

El emisor y el verificador conservan su contrato. `src/frontend.c` ahora es
la entrada publica y el despacho real de errores. La mejora conjunta solicitada
de SUPER GRAFO permite leer tambien los sitios originales de `CASM_RULE_*`
en los modulos; el Taller los presenta antes del despacho.

El modelo de trabajo baja de 1.077.280 a 361.648 bytes en Windows x64 con
Clang 23.1.2. Once invariantes de deposito y 333 casos diferenciales pasan:
HEX, IR, paquetes y diagnosticos identicos. El ejecutable HOST crece 512 bytes.
Esta medida no acredita RSS, ciclos, vatios ni memoria de Ring 0.
Ver [criterios y reproduccion](CONTROL-PERFORMANCE-ELEGANCE.md).

Consultar [RUTA-CASM](../docs/CASM-ROADMAP.md) para el alcance de CASM destinado
al kernel. Completo significa suficiente para el contrato x86-64 de BMO-X2,
con sus rechazos y pruebas; no compatibilidad total con C ni toda instruccion x86.

S1: ver [parada propia](../kernel/boot/stop/README.md). El ejecutable HOST
crece con el perfil nuevo; las medidas vigentes estan en `metrics/host-maturity.json`.
