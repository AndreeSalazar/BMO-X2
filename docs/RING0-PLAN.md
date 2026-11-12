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

| Entrega | Nodos principales | Prueba para avanzar |
|---|---|---|
| 1. Entrega y diagnostico | `boot-context`, `x86_64-cpu`, `cpu-state`, `x86_64-exceptions`, `kernel-diagnostics`, `init` | Pila propia y excepcion controlada en QEMU. Diagnostico por fase. |
| 2. Memoria y proceso | `physical-memory`, `virtual-memory`, `user-memory`, `process` | Un proceso de prueba entra en CPL3 y su fallo deja al kernel operativo. Sus marcos y capacidades se recuperan. |
| 3. Imagen y admision | `sbef`, `sbef-loader`, `image-policy` | Un ejecutable minimo arranca. Lector HOST y CASM coinciden en el mapa y los rechazos. Aplicar la politica antes de ejecutar. |
| 4. Peticiones y espera | `capabilities`, `invoke`, `x86_64-interrupts`, `time`, `sched`, `ipc`, `wait` | Una operacion autorizada, rechazos de capacidad y buffer, un despertar por senal y otro por plazo. |
| 5. Congelacion | `ring0-base-gate` | Vectores de oro de SBEF y ABI. Misma peticion desde compiladores distintos. Publicar version, registros, errores y permisos. |
| 6. Plataforma y servicios | `device-bus`, `device-storage`, `file-access`, `device-io`, `device-network`, `multiprocessor` | Pruebas por dispositivo y recursos concedidos. Medir memoria, latencia y arranque. Hardware fisico tras evidencia QEMU y recuperacion definida. |

La primera prueba de carga usa una imagen fija disponible en memoria.
Leer aplicaciones del disco agrega el contrato de bloques y archivos.
El cierre de la base permite empezar la transferencia del runtime. Cada
servicio posterior requiere sus propias operaciones y recursos probados.
[SBEF y ABI](../contracts/SBEF.md).

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
