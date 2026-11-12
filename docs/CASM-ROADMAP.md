# Ruta de CASM: suficiente para construir el kernel x86-64

Los pasos son criterios de cierre, no fechas ni porcentajes. Los contratos
se amplian cuando un programa concreto del kernel los exige.

Revision 05-11-2026: C2 esta implementado y comprobado en HOST para la
semilla metal64: lexer, simbolos, enteros y parser separados; depositos
compartidos y 333 comparaciones sin cambiar emision ni diagnosticos. Native y
las capacidades privilegiadas mantienen sus limites propios. No cierra C3..C10.

| Paso | Entrega | Cierre exigido |
|---|---|---|
| C0 | Base heredada, procedencia, nodos y banco host | Huellas registradas, saludo de oro identico, rechazos por su regla y mapa SG legible. |
| C1 | Fronteras del lenguaje y de sus perfiles | Especificar que parte de Native se reutiliza y que parte de metal64 permanece; casos de aceptacion/rechazo por perfil. |
| C2 | Frontend y semantica separados por responsabilidad | Lexico, sintaxis, nombres, tipos y enteros con interfaces pequenas; mismo HEX/IR para el banco anterior. Actualizar lectura de katanas de SG junto al reparto. |
| C3 | IR del kernel | Valores de ejecucion, control, funciones, tipos de CPU, origen fuente y trampas con formato versionado y verificador. |
| C4 | Emisor x86-64 completo para esa IR | Codificaciones, registros, ModRM/SIB, inmediatos, RIP relativo, saltos, stack y ABI por funcion; vectores independientes y limites exactos. |
| C5 | Memoria y efectos explicitos | Punteros/regions con alcance, alineacion, anchos, volatile/MMIO, atomicos y orden de memoria definidos; negativos de alias y rango. |
| C6 | Frontera privilegiada | CR/MSR, puertos, tablas de descriptores, excepciones, interrupciones y transiciones de anillo con contratos; el subconjunto requerido se prueba en QEMU. |
| C7 | Unidades y carga | Simbolos, relocaciones, regiones RX/RW/NX, entrada, trampas y formato de imagen; ningun recurso Linux implicito. |
| C8 | Arranque minimo del kernel CASM | Arranque recuperable en QEMU, salida de diagnostico y excepcion controlada. La cadena EFI se especifica y comprueba por separado. |
| C9 | Primer proceso Rust aislado | Ring 3, pila y memoria propias, llamada a CASM y retorno; fallo del proceso contenido por el kernel. |
| C10 | Autocompilacion en el sistema propio | Servicios de archivos/memoria versionados, compiler CASM adaptado, generaciones repetidas y una fuente distinta compilada sin Linux. |
| C11 | Ampliacion del kernel | Tiempo, planificacion, entrada, almacenamiento, servicios y DMA por nodo y evidencia. Metal despues de QEMU y de definir recuperacion. |

## Orden inmediato

La base C0 paso el banco aplicable en este anfitrion: 107 pruebas y una
omision Linux explicita. `kernel/boot/entry.casm` anade una fuente propia de
emision, con vector exacto; aun sin ejecucion QEMU. Ahora concretar C1 con programas pequenos que
representen lo que el kernel necesita. Native ya contiene funciones/bucles/buffers:
esa experiencia se aprovecha antes de decidir que implementar otra vez.
El inventario [x86_64/requirements.json](../CASM/x86_64/requirements.json)
define 16 necesidades y su evidencia, sin prometer toda la ISA. Implementar lo
que exige el siguiente hito; el primer recorrido esta en [FIRST-BOOT](FIRST-BOOT.md).

El parche 0.3 muestra una idea de runtime, pero le falta `verify_runtime`.
Su mera aplicacion no cierra C3. Autocompilacion Linux tampoco cierra C10.

El orden de integracion de Ring 0 es contexto y excepcion controlada,
memoria y aislamiento, carga de un SBEF minimo y dos puertas del ABI.
El contrato se congela tras comparar lectores y ejecutar el mismo caso
desde varios compiladores. [Plan de SBEF y ABI](../contracts/SBEF.md).

## Pruebas que acompanian cada ampliacion

1. Fuente valida y fuente que debe rechazarse por una regla concreta.
2. Bytes esperados independientes del emisor; extremos de signo, ancho y salto.
3. IR/HEX mutados: el verificador rechaza y no se publica paquete.
4. Ejecucion aislada cuando haya semantica de runtime; QEMU para privilegios.
5. Mapa linea -> IR -> bytes/trampa vigente para la fuente que se esta mirando.

Una instruccion desensamblada no demuestra toda su semantica. Un checksum no
demuestra origen confiable. Un caso positivo no acredita todos los aparatos.
