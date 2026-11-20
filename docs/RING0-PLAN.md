# Ring 0 de BMO-X2

La implementacion propia vive en `kernel/` y se escribe en CASM para
x86-64. El grafo distingue las piezas probadas en QEMU y los nodos de
diseno. La entrada actual detiene la CPU con 4 bytes de codigo y un
paquete de 28 bytes. El limite de la entrada sigue siendo menor de
512 bytes con cabecera. [Primer arranque](FIRST-BOOT.md).

Para cada mecanismo nuevo se conserva fuente congelada, IR, HEX, vector
independiente, rechazos y evidencia de ejecucion. El Taller CASM muestra
los offsets del artefacto verificado. Las relaciones `plan` expresan
orden de trabajo. [Catalogo de nodos](../super-grafo/CATALOG.md).

## Orden de cierre

Este es el backlog unico de mecanismos pendientes. Sus nombres de
subsistema son referencias de diseno, no acreditan nodos implementados
ni carpetas existentes. El catalogo conserva las fuentes y contratos
activos; los documentos duplicados de `contracts/plans/` se retiraron.

| Entrega | Nodos principales | Prueba para avanzar |
|---|---|---|
| 1. Entrega y diagnostico | `boot-context`, `x86_64-cpu`, `cpu-state`, `x86_64-exceptions`, `kernel-diagnostics`, `init` | Pila propia y excepcion controlada en QEMU. Diagnostico por fase. |
| 2. Memoria y proceso | `physical-memory`, `virtual-memory`, `user-memory`, `process` | Un proceso de prueba entra en CPL3 y su fallo deja al kernel operativo. Sus marcos y capacidades se recuperan. |
| 3. Imagen y admision | `sbef`, `sbef-loader`, `image-policy` | Cierre: arrancar un ejecutable minimo; cotejar lectores HOST y CASM en mapa y rechazos; aplicar la politica antes de entrar a CPL3. |
| 4. Peticiones y espera | `capabilities`, `invoke`, `x86_64-interrupts`, `time`, `sched`, `ipc`, `wait` | Una operacion autorizada, rechazos de capacidad y buffer, un despertar por senal y otro por plazo. |
| 5. Congelacion | `ring0-base-gate` | Vectores de oro de SBEF y ABI. Misma peticion desde compiladores distintos. Publicar version, registros, errores y permisos. |
| 6. Plataforma y servicios | `device-bus`, `device-storage`, `file-access`, `device-io`, `device-network`, `multiprocessor` | Pruebas por dispositivo y recursos concedidos. Medir memoria, latencia y arranque. Hardware fisico tras evidencia QEMU y recuperacion definida. |

La primera prueba de carga usa una imagen fija disponible en memoria.
Leer aplicaciones del disco agrega el contrato de bloques y archivos.
El cierre de la base permite empezar la transferencia del runtime. Cada
servicio posterior requiere sus propias operaciones y recursos probados.
[SBEF y ABI](../contracts/SBEF.md).

La entrega 1 ya tiene una prueba de pila y una IDT minima que registra
una excepcion controlada en QEMU. La entrega 2 ya prueba el ciclo de
propiedad, devolucion, borrado y reutilizacion de un marco de 4 KiB.
CASM ya selecciona seis marcos contiguos del mapa UEFI, activa tablas
propias y comprueba un alias de usuario de solo lectura y sin ejecucion
desde CPL0. Un ensayo separado ya entra a CPL3, captura el fallo de
proteccion y desmapea y borra las dos paginas del programa de prueba.
Faltan el asignador general y la reutilizacion en un segundo proceso.
[Contexto y pila](../kernel/boot/context/STACK.md) y
[primera excepcion](../kernel/arch/x86_64/exceptions/FAULT.md).
[Ciclo de un marco](../kernel/mm/physical/lifecycle/CYCLE.md) y
[tablas propias](../kernel/mm/virtual/PAGING.md).
[Fallo desde CPL3](../kernel/mm/user/USER-FAULT.md).

El ensayo ABI 1 admite un SBEF embebido, verifica dos rechazos de
admision y ejecuta INVOKE sobre SYSCALL. Las sondas posteriores de QEMU
cargan SBEF externos y prueban WAIT con entrada y plazo. El cierre exige
integrar esos mecanismos en el cargador y el ciclo de proceso propios.
[ABI de BMO-X2](../contracts/ABI.md).

La revocacion local ya tiene un ensayo separado: retira una pagina,
invalida el TLB, borra su marco, reanuda CPL3 y registra el segundo
fallo. Falta integrarla con propietarios, marcos compartidos y SMP.
[Revocacion en caliente](../kernel/mm/virtual/revoke/HOT-UNMAP.md).

Para dar paso al runtime de Ring 3 se exige un primer proceso aislado.
El kernel debe poder cargar su SBEF, darle una pila y permisos propios,
atender una peticion, despertarlo y recuperar sus recursos cuando sale
o falla. La compatibilidad de aplicaciones se prueba por capacidad.
Los controladores para escritorio, sonido y red pueden incorporarse
segun los servicios de Ring 3 los necesiten.

El [contrato Faggin](../contracts/FAGGIN.md) ordena la ruta desde reset
en 16, 32 y 64 bits. Su entrega converge con la ruta UEFI en el mismo
contrato de entrada CASM. Rust queda en el runtime y escritorio de Ring 3.

## Referencia del padre

Inventario de `Ultra_kernel_x86-64/kernel/src/ring0/` de BMO-X en
`6076bdefefc67877419ca53633c6e40cb45fc92d`. Se consultan sus contratos,
pruebas y decisiones de responsabilidad para escribir los mecanismos
de CASM.

| Familia de BMO-X | Destino en BMO-X2 |
|---|---|
| `core` | Arranque, inicializacion y diagnostico. Consola, escritorio y visualizacion se evaluan en la frontera de servicios. |
| `cpu`, `cpu_vendor` | Descubrimiento y estado de CPU. Frecuencia, energia y particularidades del equipo se prueban por perfil. |
| `plat` | Contexto, excepciones, interrupciones, tiempo y SMP. Recursos DMA e IOMMU bajo el nodo de buses. |
| `mm` | Marcos, tablas, permisos, copia de usuario y propiedad. |
| `task` | Ciclo de vida, planificador, SBEF, integridad y politica de admision. |
| `obj` | Capacidades, canales, memoria concedida y recursos de aparato con permisos. |
| `syscall` | INVOKE y WAIT. Las demas operaciones se versionan por tipo de objeto. |
| `dev` | Descubrimiento, bloques, entrada, pantalla y audio. Cada aparato requiere evidencia propia. |
| `fsys` | Frontera de bloques y archivos. Politica y formatos complejos evaluados en Ring 3. |
| `svc`, `red` | Capacidades y mecanismos minimos. Servicios y protocolos en Ring 3 segun su contrato. |
| `cabina`, `mirador`, `uconsole`, `reloj` | Diagnostico, contadores y tiempo en el kernel. Presentacion y herramientas en Ring 3. |

TALK-CPU sirve de referencia para la entrega inicial. ULTRA LinuX
aporta comparacion de compiladores y verificacion de artefactos.
[Procedencia](../heritage/TRANSFER.md) y [plan de herencia Ring 3](../heritage/RING3-TRANSFER.md).
