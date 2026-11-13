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
| Ctrl+Super+1-4 | Cambiar el espacio visible y restaurar su ultimo foco. |
| Super+1-9 | Enfocar la ventana numerada del espacio activo. |
| Super+Shift+1, Super+Shift+2, Super+Shift+3, Super+Shift+4 | Mover la ventana activa al espacio indicado y conservar el espacio visible. |

Cambiar de espacio conserva los procesos y las ventanas de los demas
espacios. Si se cerro la ventana enfocada, se usa la siguiente ventana
disponible de ese espacio. Cada espacio reserva hasta nueve atajos.
Cambiar de foco o cerrar otra ventana conserva el numero. Una ventana
que se mueve recibe el primer numero libre del destino. Si todos estan
ocupados, la ventana se puede enfocar por su identificador.

## Entrada directa

BMO-X entrega por separado caracteres y eventos crudos de tecla. El
compositor del padre reclama directamente la capacidad de entrada.
La referencia esta en `Ultra_userspace/userland/src/entrada.rs` y
`platform/abi/bmo-abi/src/syscalls/surface/entrada.rs`. BMO-X2 toma
el formato del evento y deja la politica de atajos en Ring 3.

`Keyboard::handle` recibe el scancode y la mascara de modificadores
asociada a ese evento. La fila superior usa los codigos 0x02 a 0x0A.
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

Las diez pruebas HOST verifican foco, movimiento, composicion,
limites y atajos mediante eventos de entrada.

## Vista previa en Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\view-desktop.ps1
```

La ventana usa el compositor Rust con dos superficies de muestra por
espacio. Usa Ctrl+Alt+1-4 o haz clic en el panel para cambiar de espacio.
Manten Alt para ver los numeros de las ventanas y pulsa Alt+1-9 para
cambiar el foco. En este visor Alt representa Super y deja Win a
Windows. El compositor reutiliza los buffers y dibuja por evento.

## Telemetria

El visor lee CPU y RAM de Windows una vez por segundo y las identifica
como HOST. La CPU se calcula entre muestras de tiempos acumulados.
La RAM usa el porcentaje fisico del anfitrion. El muestreo actualiza
solo el texto del panel y los fallos de lectura se muestran como `--`.

Ring 0 comprueba CPUID y el ciclo de marcos en perfiles de QEMU. Para
publicar metricas al escritorio, primero necesita contadores del
asignador integrado y tiempos activo e inactivo del planificador.
La interfaz prevista es una capacidad de lectura por INVOKE con una
instantanea versionada, un tiempo monotono y campos disponibles.
El escritorio puede sumar componentes conforme el kernel los
publique. La politica de muestreo y presentacion queda en Ring 3.
El numero de operacion y el formato binario quedan pendientes de la
primera prueba de la capacidad en QEMU.

## SBEF de prueba

El ejecutable de prueba usa el mismo crate, ejecuta dos cambios de
espacio con eventos fijos, coteja los pixeles y llama al stub INVOKE
del ABI 1. Su salida provisional es una trampa al retornar de la entrada.
El script usa Rust freestanding con panico abortado, LLVM y el
empaquetador SBEF. El linker conserva la comprobacion de secciones
incompatibles y LTO elimina las tablas de desenrollado sobrantes.

```powershell
rustup target add x86_64-unknown-none
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1
```

En el HOST de referencia salio `build/desktop/desktop.sbef` de 1491 bytes,
con regiones RX y R. La prueba de arranque actual de CASM carga su propio
SBEF embebido. Queda cargar el ejecutable externo, conectar el teclado
de QEMU y presentar cuadros de forma continua.

## Primer cuadro en QEMU

El perfil de prueba usa un SBEF Rust de 1552 bytes embebido en el
paquete de arranque. Despues de la intro HD, el compositor en CPL3
cambia entre dos espacios con eventos fijos y produce dos colores.
El presentador del ensayo copia esos colores al framebuffer al
terminar. QEMU verifica 4096 pixeles y el borrado de las paginas de
usuario. El cargador externo y la presentacion continua con teclado
real quedan pendientes.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile desktop-intro -Wait
```

Para generar el ensayo, ejecuta `tools/build-desktop.ps1 -Guest`
con `-AbiRun` apuntando al run de `bmo-x2.ps1 -Accion abi` y
`-IntroRun` al de `bmo-x2.ps1 -Accion gato-hd`.

## Sesion interactiva en QEMU

El perfil de sesion arranca un SBEF Rust embebido de 1976 bytes despues
de la intro. Dibuja un panel con cuatro espacios y dos ventanas de
muestra. QEMU verifica el cambio con Ctrl+Super+1-4, el foco con
Super+2 y su restauracion al volver. Las teclas 1-4 tambien cambian de
espacio si Windows intercepta los atajos con Super.

El raton PS/2 mueve un puntero dibujado por software. El clic
izquierdo enfoca una ventana. QEMU verifica el movimiento, la
limpieza de la posicion anterior y el cambio de foco. El viewport
logico de 640 por 400 se dibuja a escala 2x en 1280 por 800.
El prototipo redibuja al mover el puntero. Queda limitar el dano a
los rectangulos anterior y nuevo antes de medir la latencia.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile desktop-session -Wait
```

Para construir la sesion, usa `-Session -AbiRun <run-abi>
-IntroRun <run-gato>` con `tools/build-desktop.ps1`. Genera el run
de la intro compacta con `bmo-x2.ps1 -Accion gato`. El paquete
observado ocupa 4087 de los 4096 bytes del puente.

La puerta de prueba concede dos permisos fijos al cliente unico.
Pantalla autoriza el dibujo y entrada autoriza la lectura PS/2.
Antes de dibujar, la sesion comprueba en CPL3 que no puede usar
pantalla para leer, entrada para dibujar, un identificador cero
para dibujar ni una operacion fuera del contrato de entrada.
El cliente de prueba usa un viewport de 640 por 400 y solicita
rectangulos acotados a una puerta experimental. El arranque y la
verificacion usan VGA emulada, con renderizado por CPU. La entrada
PS/2 se consulta por sondeo. El cargador externo, la entrada por
eventos, la integracion con el compositor completo y la telemetria
siguen pendientes.
