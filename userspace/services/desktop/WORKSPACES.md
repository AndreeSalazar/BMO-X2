# Espacios de trabajo del escritorio

El servicio de escritorio de Ring 3 toma las decisiones de ventanas y
foco. El supervisor de sesion inicia y recupera el servicio. El
planificador de Ring 0 administra CPU y el subsistema de entrada entrega
eventos mediante las interfaces concedidas.

## Control de pantalla

El compositor Rust decide que superficies se muestran, su orden,
geometria y foco. El primer perfil enlaza los componentes en el mismo
proceso. Entregan superficies prestadas y reciben acciones por llamadas
directas. El compositor escribe un cuadro en un buffer de RAM.
La presentacion en BMO-X2 usara una capacidad de pantalla de Ring 0.
El kernel controla el dispositivo, las interrupciones y los rangos DMA.

El primer perfil compone por software en QEMU, con dos superficies,
entrada y los cuatro espacios. Despues se incorporan el panel, el
lanzador, las notificaciones, el fondo y la configuracion de pantalla.
Ultra-LinuX aporta la interaccion y el diseno del escritorio. Las
dependencias de sus componentes se revisan antes de portarlas.

Una biblioteca C puede enlazarse con el mismo proceso mediante un
adaptador con ABI C. El compositor conserva la propiedad del buffer
y la capacidad de presentar. La composicion inicial esta en Rust.
[Frontera DMA](../../../kernel/drivers/bus/DMA.md)

Del padre se toma la division entre decision de ventanas, recorte y
presentacion. Director separa su escena del manejo de comandos en
`Ultra_userspace/services/director/src/main.rs`. El lienzo de
`platform/shared/bmo-dibujo/src/lienzo.rs` recorta en una frontera comun.
`Ultra_userspace/userland/src/pantalla/mod.rs` documenta el dibujo
sobre un buffer propio y la presentacion posterior. Esas rutas
sirven como referencia para las interfaces de BMO-X2.

## Atajos

El perfil inicial ofrece cuatro espacios numerados. La referencia de
Ultra-LinuX es `src/rootfs/desktop/hyprland.lua`, revision `7c275c1`,
que usa Super con numeros para enfocar y Super+Shift para mover ventanas.

| Atajo | Operacion |
|---|---|
| Super+1, Super+2, Super+3, Super+4 | Cambiar el espacio visible y restaurar su ultimo foco disponible. |
| Super+Shift+1, Super+Shift+2, Super+Shift+3, Super+Shift+4 | Mover la ventana activa al espacio indicado y conservar el espacio visible. |

Cambiar de espacio conserva los procesos y las ventanas de los demas
espacios. Si se cerro la ventana enfocada, se usa la siguiente ventana
disponible de ese espacio. Los cuatro espacios forman el primer perfil
de prueba.

## Entrada directa

BMO-X entrega por separado caracteres y eventos crudos de tecla. El
compositor del padre reclama directamente la capacidad de entrada.
La referencia esta en `Ultra_userspace/userland/src/entrada.rs` y
`platform/abi/bmo-abi/src/syscalls/surface/entrada.rs`. BMO-X2 toma
el formato del evento y deja la politica de atajos en Ring 3.

`Keyboard::handle` recibe el scancode y la mascara de modificadores
asociada a ese evento. La fila superior usa los codigos 0x02 a 0x05.
Al pulsar un atajo, el escritorio consume la pulsacion, su repeticion
y la liberacion correspondiente, incluso si se suelta Super primero.
Las otras combinaciones se devuelven para que el componente enfocado
pueda recibirlas. El adaptador rechaza eventos con bits reservados o
sin marca de presencia. Al reemplazar la fuente de entrada se puede
reiniciar el estado local del teclado.

La conexion prevista es una capacidad de entrada concedida al
compositor, seguida de llamadas directas a su nucleo Rust. La
mascara se debe asociar al evento al producirlo. La consulta de
modificadores de BMO-X devuelve el estado del momento y sirve de
referencia para el formato de bits.

## Comprobacion HOST

El crate `bmo-x2-desktop` ya compone superficies opacas XRGB8888 en
filas contiguas. Su estado y sus buffers se prestan por referencias
de Rust. La capacidad maxima de ventanas la elige quien instancia
el escritorio. Cambiar de espacio selecciona el foco de ese espacio.
Mover una ventana conserva el espacio visible.

```powershell
New-Item -ItemType Directory -Force .\build\desktop | Out-Null
rustc --edition=2024 --test -D warnings .\userspace\services\desktop\src\lib.rs -o .\build\desktop\desktop-tests.exe
.\build\desktop\desktop-tests.exe
```

Las nueve pruebas HOST verifican foco, movimiento, composicion,
limites y atajos mediante eventos de entrada. Queda enlazar el
proceso como SBEF, presentarlo en QEMU y conectar la capacidad
de entrada al teclado real.
