# Kernel: Ring 0 en CASM

Estado: DISENO. Los subnodos fijan responsabilidades y pruebas; no contienen
todavia implementacion de kernel. Se construyen despues de ampliar CASM con
las operaciones y contratos que necesitan. Rust no se enlaza a este Ring 0.

La primera fuente propia es `boot/entry.casm`: sonda metal64 de emision HOST,
con servicio de salida del cargador. No equivale a un kernel arrancado.

Orden: boot -> arch/x86_64 -> exceptions/mm -> capabilities -> syscalls.
`init/` ordenara las fases; `time/`, `sched/`, `ipc/` y `drivers/` tienen sus
fronteras reservadas para crecer cuando el recorrido minimo los necesite.

El primer hito de ejecucion es la entrada CASM observada en QEMU, con una
parada controlada. Despues vienen excepciones e aislamiento de un proceso Rust.
Ver [FIRST-BOOT](../docs/FIRST-BOOT.md).
