# CASM en BMO-X2

Esta pagina manda sobre los estados heredados de los README de origen.
Esos documentos conservan la fecha, el entorno y el alcance de su trabajo.

| Perfil | Fuentes | Lo disponible | Lo que no acredita |
|---|---|---|---|
| metal64 0.2 | `src/`, `verify.py`, `test.py` | Semilla C11, enteros constantes exactos, HEX e IR, paquete FAGRAW64 comprobado. | Kernel completo, variables de ejecucion, MMIO o cambios de privilegio. |
| Native 0.1 | `native/` | Compilador CASM, funciones, bucles, buffers, guardas; autocompilacion documentada en Linux. | Autocompilacion nueva en Windows o dentro de BMO-X2. |
| Native freestanding | `native/freestanding.py` | Adaptador sin servicios Linux, con permisos y trampas declarados. | Imagen EFI ni kernel; sigue necesitando cargador y manejador #UD. |
| metal64 0.3 | `traspaso/` | Parche de investigacion con RDTSC y trampas. | Verificador completo: NO se ha aplicado al compilador de esta copia. |

## Primera base reproducible

Revision HOST del 05-11-2026: el frontend metal64 esta repartido en lexer,
simbolos, enteros y parser, con tipos y almacenamiento en `src/model/`.
`sources.json` alimenta las construcciones Windows y Linux e incluye las
cabeceras en la vigencia de la cache. [Fronteras del frontend](src/frontend/README.md).

`catalog.json` organiza 45 elementos jerarquicos. El build valida el catalogo
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
