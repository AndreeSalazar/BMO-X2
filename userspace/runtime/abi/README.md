# ABI de aplicaciones

- `include/bmo_abi.h`: encabezado comun C/C++ de INVOKE y WAIT.
- `sysv/`: entrada ELF64, portal y vector HEX cotejado.
- `win64/`: entrada PE32+ freestanding y portal Rust para Microsoft x64.

El cargador inicia un SBEF con la pila alineada. Cada entrada establece
la convencion de llamada de su cliente. Ambos portales usan el mismo
[contrato de llamadas del kernel](../../../contracts/ABI.md).

## Compatibilidad PE32 x86

La ruta prevista aloja el programa PE32 como invitado de un proceso
nativo x86-64 en Ring 3. El runtime de usuario interpreta o traduce
sus instrucciones y mantiene sus registros, pila y direcciones de
32 bits. Las llamadas Win32 pasan por adaptadores de ese runtime.
Los adaptadores validan los rangos invitados antes de acceder a
memoria y usan capacidades del proceso al pedir servicios mediante
INVOKE y WAIT. El nano-core protege el proceso x86-64 y valida sus
capacidades, permisos y argumentos por el ABI vigente.

HOST ya inspecciona PE32 y reporta esa ruta como pendiente. El primer
ensayo en QEMU debe cargar un PE32 minimo, llamar a una importacion
desde el codigo invitado, comprobar su resultado y rechazar un
puntero fuera del espacio invitado. La traduccion, los adaptadores
Win32 y la ejecucion de StarCraft quedan pendientes.
