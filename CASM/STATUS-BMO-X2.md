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

`bmo-x2.ps1 -Accion comprobar` construye metal64 con Clang del anfitrion y
corre el banco heredado. La adaptacion de `test.py` para Windows omite
explicitamente el caso de RLIMIT_DATA; no imita el limite ni lo cuenta aprobado.
En Linux se conserva ese caso. La generacion Native se vuelve a probar en su
taller Linux/QEMU; no se ejecutan ELF Linux en Windows.

`bmo-x2.ps1 -Accion compilar` congela fuente y herramientas, emite HEX e IR,
verifica y publica `INICIO.X86` solo si el verificador acepta. SUPER GRAFO
puede leer esa compilacion en `build/CASM/run-*` y mostrar linea -> bytes.

La organizacion inicial conserva los archivos del emisor para mantener ese
panel operativo. Lexico, sintaxis y enteros todavia comparten `src/frontend.c`;
su separacion fisica se hara con pruebas de equivalencia de bytes y soporte
del Taller CASM para leer las reglas distribuidas.

Consultar [RUTA-CASM](../docs/CASM-ROADMAP.md) para el alcance de CASM destinado
al kernel. Completo significa suficiente para el contrato x86-64 de BMO-X2,
con sus rechazos y pruebas; no compatibilidad total con C ni toda instruccion x86.
