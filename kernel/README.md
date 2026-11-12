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

QEMU ya ejecuta Genesis, la parada propia y la sonda CPUID emitida por
CASM. La sonda genera un perfil observado a traves del banco de arranque.
La pila propia, las excepciones y los demas mecanismos siguen en diseno.
[Sonda de CPU](arch/x86_64/cpu/PROFILE.md) y [plan de Ring 0](../docs/RING0-PLAN.md).
