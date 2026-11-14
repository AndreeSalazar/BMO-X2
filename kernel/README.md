# Kernel: Ring 0 en CASM

| Carpeta | Responsabilidad |
|---|---|
| `boot/` | Entrada acotada, contexto de entrega y evidencia del puente. |
| `arch/x86_64/` | Identificacion de CPU, contexto, excepciones e interrupciones. |
| `init/`, `diagnostics/` | Orden de fases y registro de fallos. |
| `mm/`, `process/`, `loader/` | Memoria, aislamiento y carga SBEF. |
| `capabilities/`, `syscalls/`, `security/` | Autoridad, puertas y admision. |
| `time/`, `sched/`, `ipc/` | Reloj, ejecucion y comunicacion. |
| `drivers/`, `storage/` | Dispositivos, bloques y acceso a archivos. |

## Perfil del escritorio

- [CPU x86-64](arch/x86_64/cpu/PROFILE.md) descubre la geometria L1 y la
  conserva en el contexto de arranque.
- [Puente UEFI](boot/bridge/desktop_media_read.S) prepara el contexto y
  lee la imagen SBEF de FAT32.
- [Cargador](loader/external_sbef.S) valida la imagen antes de copiarla
  a marcos de RAM y publicar sus permisos para Ring 3.
- [Puerta](syscalls/session_gate.S) atiende INVOKE y WAIT. El build
  comprueba su limite de 2048 bytes de codigo maquina.
- [Bus](drivers/bus/xhci_inventory.inc) contiene el inventario xHCI.

Estas extensiones de prueba se ensamblan con LLVM. `tools/` construye
los paquetes y ejecuta QEMU. Los perfiles propios emitidos por CASM
tienen sus fuentes, vectores y evidencia junto a cada subsistema.

QEMU ya ejecuta Genesis, la parada propia y la sonda CPUID emitida por
CASM. La sonda genera un perfil observado a traves del banco de arranque.
La entrada de contexto ya selecciona una pila dentro de la reserva del
puente y rechaza una entrega nula. La primera IDT propia registra el RIP
de una excepcion controlada. [Sonda de CPU](arch/x86_64/cpu/PROFILE.md),
[primera excepcion](arch/x86_64/exceptions/FAULT.md),
[pila inicial](boot/context/STACK.md) y [plan de Ring 0](../docs/RING0-PLAN.md).

El [gato de arranque](boot/splash/README.md) demuestra dibujo directo
en Ring 0 con 508 bytes de paquete y tres cuadros observados en QEMU.
