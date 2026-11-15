# Frontera de ejecucion de BMO-X2

NANO-CORE nombra el diseno acotado de la base privilegiada de Ring 0.
HOST prepara imagenes fuera de esa base. Ring 3 aloja servicios,
runtimes y aplicaciones con capacidades concedidas por el nucleo.
La portabilidad entre CPUs no es requisito: BMO-X2 se especializa en
x86-64. [Identidad y estado del diseno](../README.md#identidad-nano-core-host-aislado-y-ring-3-abierto).

| Lugar | Responsabilidad | Artefacto que cruza la frontera |
|---|---|---|
| `tools/host/` en HOST | Inspeccionar ELF64 y PE32+, explicar incompatibilidades y empaquetar el ELF64 admitido. | SBEF y un informe de diagnostico para el desarrollador. |
| `kernel/` en Ring 0 | Orquestador CASM. Controla memoria, admision SBEF, transiciones de CPU, excepciones, capacidades e IPC. | Imagen SBEF comprobada hacia CPL3. Peticiones y respuestas del ABI. |
| `userspace/supervisor/` en Ring 3 | Supervisor Rust previsto. Decide orden de servicios, reinicio, configuracion y distribucion de las capacidades que recibe. | Peticiones al kernel por INVOKE y WAIT. Politica y errores de servicio para las aplicaciones. |
| `userspace/runtime/`, `services/`, `apps/` | Inicio, bibliotecas, servicios y aplicaciones de usuario. Los formatos de datos pertenecen al consumidor de Ring 3. | Binarios SBEF para ejecutar y mensajes para interactuar. |

## Autoridad y admision

El encabezado SBEF describe la unica imagen de usuario que el cargador
CASM admitira. Describe rangos, permisos y version del ABI. Un encabezado
puede pedir recursos. La politica de capacidades en Ring 0 decide que
autoridad recibe el proceso. El supervisor puede administrar y delegar
los recursos concedidos por ese contrato.

Los binarios ELF y PE son entradas de herramientas de importacion. Las
dependencias de formato, sistema operativo y runtime se resuelven antes
de ejecutar. Un archivo de datos permanece bajo el servicio que lo
consume. El kernel valida rangos y capacidades cuando ese servicio
solicita acceso a memoria, archivos o dispositivos.

El proceso entra en CPL3 tras la admision. El kernel interviene
en operaciones protegidas y excepciones. Los formatos de scripts
y datos se interpretan en el proceso o servicio de Ring 3.
[Reglas de Ring 3](../userspace/POLICY.md).

SUPER GRAFO comprueba que los nodos CASM de Ring 0 viven en `kernel/`,
los nodos de Ring 3 en `userspace/` y las relaciones de codigo que
salen de Ring 0 apuntan a Ring 0 o a un contrato. Las relaciones de
verificacion siguen conectando el cargador con el lector HOST.

## Medidas y estado

La prueba actual de aislamiento pesa 716 bytes de codigo, 740 de
paquete y usa 32 KiB dentro de la reserva del puente. Los 256 MiB
configurados para QEMU son la capacidad de la VM. En una ejecucion
integrada se mediran por separado el kernel, sus tablas, pilas y
metadatos, y las paginas del supervisor y sus servicios. Los
importadores se ejecutan en HOST y se contabilizan alli.

El ensayo CASM admite un SBEF embebido. El perfil integrado de escritorio
usa extensiones LLVM para leer un SBEF externo de FAT32, mapearlo en RAM
y bloquear en WAIT con el PIT. Quedan integrar ese cargador y la puerta
en CASM, asignar marcos por proceso y conectar el supervisor Rust.
[Plan de Ring 0](RING0-PLAN.md) | [Perfil SBEF HOST](../contracts/SBEF-HOST.md)
