# Rutas de arranque y contrato Faggin

El kernel de destino es CASM x86-64. En la ruta probada, UEFI entrega
modo largo al puente heredado, que obtiene el mapa y el framebuffer,
cierra BootServices y llama a la entrada CASM. Genesis, la parada, la
identificacion de CPU, la pila y el gato tienen pruebas QEMU separadas.

La ruta propia desde reset sigue en diseno. TALK-CPU aporta las
transiciones de modo y BMO-X aporta la division por responsabilidades.
La cadena activa de BMO-X usa dos etapas de preparacion, `s1_cpu` y
`s2_mem`, tras UEFI. El inventario historico de doce etapas del padre
sirve de referencia para separar contratos.

| Etapa propia | Entrega a la siguiente | Evidencia requerida |
|---|---|---|
| 16 bits desde reset | Pila temporal, A20 y una GDT preparada. El salto entra al segmento de 32 bits. | QEMU observa el punto de entrada, los limites de la pila y el primer destino protegido. El vector identifica modo, prefijos y salto. |
| 32 bits protegido | Segmentos y pila, tablas iniciales, PAE y entrada a modo largo. | QEMU registra CR0, CR3, CR4, EFER y el selector al cambiar de modo. Las reservas de tablas y pila no se solapan. |
| 64 bits de entrega | Pila alineada, contexto versionado y rangos de memoria. Framebuffer opcional segun el camino de arranque. | La entrada CASM verifica el contexto. Una IDT propia registra una excepcion controlada. |

Cada etapa lleva su propia fuente, IR con modo declarado, vector de
bytes y mapa de instrucciones y datos. Los offsets y direcciones se
cierran junto con el contrato de carga. Las transiciones se prueban en
QEMU antes de unir las etapas. En la ruta desde reset, un framebuffer
requiere una entrega propia o de firmware compatible.

Las dos rutas convergen en el contrato de entrada x86-64. El limite
menor de 512 bytes pertenece al paquete de entrada. El gato de
resolucion alta es un paquete grafico de demostracion con su propio
limite de 4096 bytes para el puente.

## Frontera de Ring 3

CASM emite el kernel y sus mecanismos de CPU, memoria y admision.
Rust se ejecuta en Ring 3 del sistema de destino para runtime,
servicios, compositor, escritorio y aplicaciones. El escritorio
recibe superficies y eventos por capacidades del ABI. Se incorpora
tras probar aislamiento, SBEF, INVOKE y WAIT.

Referencias del padre en `Ultra_kernel_x86-64/faggin/README.md` de BMO-X
y de TALK-CPU en `Orquestador_Metal/16-bit/` y `Orquestador_Metal/32-bit/`.
[Intel SDM, inicializacion de IA-32e](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).
