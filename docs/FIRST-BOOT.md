# Primer hito: una entrada propia y un fallo explicado

## Prueba de escritorio Hoja

El perfil `-Sheet` agrega un icono de documento arriba a la izquierda.
Dos clics seguidos abren la hoja y Esc vuelve al escritorio. QEMU
comprueba que un clic aislado deja el escritorio abierto. La vista es
una demostracion de Ring 3 y usa raton PS/2 emulado.

Desde la raiz de BMO-X2 en PowerShell 5.1:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1 -Session -External -Sheet -AbiRun build/CASM/run-20261112-174958-944cb997
$sheetPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $sheetPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-3c09ddaa8ea6 --sheet-desktop build/desktop/desktop-sheet.sbef
```

Abre el run impreso con `tools/boot/view.ps1 -Run <ruta-del-run>`.
El perfil cabe en las dos paginas de texto del escritorio. Durante el
ensayo cede el espacio del indicador de entrada al lanzador de Hoja.

## Primera prueba en hardware

### Perfil experimental de reinicio xHCI

`stage_desktop_media.py --xhci-reset-probe` genera
`diagnostic-media/` con una sonda limitada al AMD `1022:149C` y
al xHCI emulado `1B36:000D`. Tras salir de UEFI comprueba la
entrega del controlador, espera CNR, detiene el controlador, solicita
HCRST y verifica que el controlador queda detenido y admite paginas
de 4 KiB. Usa espera acotada por iteraciones. Falta medir el plazo
de respuesta en el AMD.

La primera linea del aviso de entrada muestra `XHCI REINICIO OK`,
`XHCI FALLO REINICIO` o `XHCI SIN ENTREGA UEFI`. El controlador
queda detenido tras un reinicio correcto. Este perfil aun carece
de colas DMA activas y enumeracion HID. Para la prueba fisica se
necesitan la foto del aviso y el BOOTLOG.TXT V3.

La foto en el equipo mostro `XHCI REINICIO OK` y ambos indicadores
PS/2 en espera. El BOOTLOG V3 registro el AMD `1022:149C` en
`2B:00.3` con BAR de memoria de 64 bits y base `0xFC200000`.
El perfil de reinicio ahora muestra `USB PUERTOS` con la cantidad de
puertos que mantienen CCS despues de HCRST. Ese censo precede a la
asignacion de ranuras y la lectura de descriptores.

### Perfil experimental de transporte xHCI

`stage_desktop_media.py --xhci-transport-probe` prepara una prueba finita
para AMD `1022:149C` o QEMU `1B36:000D`. Usa el escritorio externo normal.
Reserva diez paginas de LoaderData (40 KiB), verifica sus limites y
solapamientos, toma la entrega UEFI y reinicia el controlador. Lee RTSOFF
y DBOFF en vez de imponer las posiciones del emulador. Admite registros
en los primeros 64 KiB del dispositivo, incluso dentro de la primera
pagina, alineados y contenidos en las paginas mapeadas. Verifica que los
bancos usados no invadan registros operacionales o puertos ni se solapen
entre ellos. Rechaza solapamientos con memoria de firmware no MMIO.

Publica un unico No Op y espera una terminacion de comando con tipo,
puntero y codigo correctos. Consume cambios de puerto intermedios sin
confundirlos con la respuesta. Tras activar las colas solicita parada, revoca PCI
Bus Master y elimina los alias MMIO. La memoria DMA permanece reservada
durante este arranque. Estas comprobaciones no sustituyen una IOMMU.
Las esperas tienen limite de iteraciones; el plazo real en AMD sigue
pendiente. La capacidad de scratchpads de esta prueba es cuatro paginas.

| Aviso visible | Resultado o ultima fase alcanzada |
|---|---|
| `XHCI DMA OK` | Respuesta validada y parada confirmada. |
| `XHCI DMA GUARDA` | Entrega, dispositivo o reserva DMA no admitidos. |
| `XHCI DMA MAPA` | Geometria de los bancos MMIO no admitida. |
| `XHCI MAPA RUNTIME` | Pagina runtime en conflicto con el mapa UEFI. |
| `XHCI MAPA DOORBELL` | Pagina doorbell en conflicto con el mapa UEFI. |
| `XHCI DMA SCRATCHPADS` | El controlador pide mas de cuatro paginas auxiliares. |
| `XHCI RELOJ ESPERA` | El temporizador de estabilizacion no respondio; prueba detenida. |
| `XHCI PUERTOS ESPERA` | No hubo un conjunto conectado y estable dentro de 1 segundo. |
| `XHCI DMA REINICIO` | No termino el reinicio. |
| `XHCI DMA ARRANQUE` | No se confirmo la salida de HCHalted. |
| `XHCI DMA RESPUESTA` | No llego una terminacion valida dentro del limite. |
| `XHCI DMA PARADA` | Llego la respuesta, pero no se confirmo la parada. |

La evidencia QEMU esta en `kernel/drivers/bus/evidence/transport-qemu.json`.
Verifica dos puertos conectados, respuesta No Op, parada, revocacion de
Bus Master, retirada de alias y rechazo de SBEF W+X. Las sondas HID
separadas conservan sus pruebas de teclado (260 informes con vuelta del
anillo) y raton (movimiento y botones). Sus resultados siguen siendo QEMU.
La nueva imagen aun no habilita entrada USB en el equipo fisico.

La siguiente prueba fisica mostro `XHCI DMA MAPA` y tres puertos
conectados. BMO-X documenta ERDP en `0xFC2004F8`, que implica RTSOFF
`0x4C0` para esta base. La sonda anterior exigia offsets de al menos
`0x1000`; esa restriccion del prototipo rechazaba bancos compactos.
Se reemplazo por comprobaciones de limites y solapamiento. La referencia
de registros es la [especificacion xHCI, secciones 5.3.7 y 5.3.8](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/extensible-host-controler-interface-usb-xhci.pdf).
`tools/boot/test_xhci_layout.py` ejecuta el validador ensamblado real en
HOST con bancos compactos y casos invalidos. No simula el controlador.
La nueva disposicion aun necesita confirmacion en AMD.

La siguiente foto fisica confirmo `XHCI DMA OK`, con `USB PUERTOS 0`.
Eso acredita la terminacion No Op y la parada, pero no la presencia de HID.
El censo anterior ocurria al terminar una prueba breve y detener el xHC.
La version de espera fija verifica PP cuando PPC admite control de alimentacion,
activa los puertos que lo necesitan sin escribir los bits RW1C, PED o PR,
y espera veinte intervalos PIT de algo mas de 10 ms antes del censo.
Usa el canal 2, sin IRQ y sin alterar el canal 0 del escritorio. Restaura
los bits de gate y altavoz del puerto 61h. No reconstruye una programacion
previa del canal 2; este perfil de arranque carece de consumidor de audio.

La cuenta se conserva mientras el xHC sigue activo y CNR esta despejado.
Despues se verifica el No Op, se detiene el xHC y se revoca Bus Master.
QEMU verifica veinte intervalos y el estado activo durante el censo.
`--xhci-timer-fault` junto con `--xhci-transport-probe` desactiva el PIT en
QEMU y comprueba la salida acotada con parada y revocacion de DMA.
Ese ensayo se guarda en `qemu-only/`, separado de la imagen para metal.
La espera estabiliza la observacion inicial; no es aun un algoritmo de
debounce que compruebe 100 ms continuos por cada puerto, ni enumera HID.
El nuevo censo fisico sigue pendiente.

### Estabilizacion adaptativa por puerto

La foto posterior confirma dos puertos conectados y `XHCI DMA OK` en
metal con la espera fija. La nueva version mantiene un contador por
puerto, muestrea cada >=10 ms y termina cuando hay al menos un puerto
conectado, todos los conectados llevan >=100 ms sin cambio observado
y los puertos tienen alimentacion. Un puerto vacio con PP activo no
bloquea a los que ya estan listos. CCS desconectado, PP perdido o CSC
reinician el contador correspondiente. CSC se reconoce por separado
sin escribir otros bits de cambio o reset. No se resetea el reloj de
los demas puertos cuando cambia uno.

La primera observacion conectada inicia el contador; diez intervalos
posteriores acreditan el tiempo estable. QEMU completa ese caso en
11 intervalos, unos 110 ms. El limite total es 100 intervalos, unos
1000 ms; sin puertos listos devuelve `XHCI PUERTOS ESPERA`, detiene
el xHC y revoca Bus Master. `--xhci-empty-ports` prueba ese limite en
QEMU sin dispositivos USB y se guarda en `qemu-only/`. El limite de
un segundo es una politica acotada de esta sonda, no una garantia
universal para todos los dispositivos USB.

Ring 0 mide, lee PORTSC y decide la transicion. La llamada INVOKE de
diagnostico existente inicia la sonda y las consultas existentes
devuelven estado y censo. No se agregan numeros de syscall. Durante
este arranque la operacion sigue siendo sincrona y sondea el PIT.
Falta una maquina de estados de enumeracion y hotplug que avance por
eventos y permita al servicio Ring 3 dormir mediante WAIT. Los
dispositivos que se conecten despues de cerrar esta sonda quedan
fuera de su observacion. Aun no hay entrada HID en metal.

`tools/boot/test_xhci_debounce.py` ejecuta el mismo helper ensamblado
con secuencias de conexion, rebote, CSC persistente, perdida de power
y 255 puertos. Son pruebas HOST de la decision; QEMU prueba el PIT,
la espera acotada, el No Op y la retirada de DMA. El nuevo tiempo
adaptativo aun necesita observacion fisica. Referencia para el
reinicio del intervalo de estabilidad ante desconexion:
[debounce del nucleo Linux](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/b91872c56940950a6a0852e499d249c3091d4284/drivers/usb/core/hub.c).

Para reproducir en PowerShell 5.1 desde BMO-X2:

```powershell
$usbPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1 -Session -External -AbiRun build/CASM/run-20261112-174958-944cb997
# Usar como tercer argumento el run-desktop impreso por el build anterior.
& $usbPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-03ce37eeb426 --xhci-transport-probe --ram-mib 256
```

El resultado se guarda en `diagnostic-media/`. El visor `tools/boot/view.ps1`
reproduce ahora los mismos dispositivos USB de cada perfil. Para avanzar
en metal hace falta la foto del aviso completo, junto con el BOOTLOG V3.
Ese archivo se escribe antes de ExitBootServices y no registra el resultado
posterior del transporte. El siguiente paso, tras confirmar `XHCI DMA OK`
en AMD, es direccionar ambos HID y armar sus endpoints de interrupcion.

### Enumeracion inicial AMD: direccion y descriptores

`--xhci-enum-probe` es una fase distinta del No Op. Conserva la admision
AMD `1022:149C` / QEMU `1B36:000D`, los bancos MMIO descubiertos, el
debounce y la reserva DMA de 40 KiB. Selecciona el primer puerto raiz
USB2 conectado con velocidad estandar baja, completa o alta. Solicita
reset sin copiar PED ni los bits RW1C, permite recuperacion del puerto,
habilita una ranura y ejecuta Address Device. No atraviesa hubs.

Lee primero 8 bytes del descriptor de dispositivo con el MPS por defecto
de la velocidad. Comprueba bMaxPacketSize0 y ejecuta Evaluate Context
sobre EP0 antes de leer los 18 bytes completos. Despues lee la cabecera
de configuracion y su contenido completo, limitado a 512 bytes. Es la
secuencia indicada para EP0 por la [especificacion xHCI, secciones 4.6.5
y 4.6.7](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/extensible-host-controler-interface-usb-xhci.pdf).
Las terminaciones deben coincidir en tipo, ranura, puntero y codigo;
los cambios de puerto intermedios se consumen sin confundirlos con ellas.
Las transferencias requieren longitud exacta. No se reutiliza el anillo
ni se permite rebasar su segmento de eventos en este ensayo finito.

La sonda ocupa 4096 B dentro de su pagina RX de 4096 B. No se ha ampliado
esa guarda ni el limite de 2 KiB de la puerta de syscall. Tras la prueba,
tanto si tiene exito como si falla, se solicita parada, se revoca Bus
Master y se retiran los alias MMIO. Las esperas de reset y terminaciones
siguen acotadas por iteraciones; su plazo real en AMD no esta medido.

QEMU verifica alta velocidad (MPS 64), velocidad completa (MPS 8), los
descriptores obtenidos, Evaluate Context, parada y retirada de DMA. Sin
perifericos verifica el plazo de descubrimiento; SBEF W+X sigue rechazado.
La evidencia esta en `kernel/drivers/bus/evidence/enumeration-qemu.json`.
Todavia no hay evidencia de esta fase en AMD.

| Aviso al terminar | Fase que debe investigarse |
|---|---|
| `USB RESET PUERTO` | Seleccion o reset del puerto raiz USB2. |
| `USB ENABLE SLOT` | Terminacion de Enable Slot. |
| `USB ADDRESS DEVICE` | Direccion y contexto inicial EP0. |
| `USB EP0 CABECERA` | Lectura inicial de 8 bytes o MPS no admitido. |
| `USB EP0 EVALUATE` | Actualizacion del MPS de EP0. |
| `USB DEVICE DESCRIPTOR` | Descriptor completo de dispositivo. |
| `USB CONFIG CABECERA` | Cabecera, longitud o solicitud de configuracion. |
| `USB CONFIG COMPLETA` | Transferencia completa o longitud inconsistente. |
| `USB DESCRIPTORES OK` | Se leyeron dispositivo y configuracion; xHC detenido. |
| `USB FALLO PARADA` | No se confirmo HCHalted; Bus Master revocado igualmente. |

Este resultado no configura HID ni habilita el teclado o raton. Tampoco
enumera ambos a la vez. Faltan validar interfaces de los descriptores en
Ring 3, SET_CONFIGURATION, SET_PROTOCOL, los endpoints interrupt IN y la
recepcion continua de ambos dispositivos. Leer una configuracion no
equivale a seleccionarla. La siguiente prueba AMD debe conservar una
foto de la fase visible; BOOTLOG V3 se escribe antes de ExitBootServices
y no contiene estos resultados posteriores.

```powershell
$usbPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $usbPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-ab5e8222cf60 --xhci-enum-probe --ram-mib 256
```

El directorio `diagnostic-media/` impreso contiene los tres archivos de
esta prueba. Los casos sin perifericos o con fallo PIT quedan solamente
en `qemu-only/`; no son imagenes para desplegar en metal.

### Diagnostico visible de teclado y raton

El puente UEFI escribe `\BMO-X2\BOOTLOG.TXT` en el volumen de arranque
antes de ExitBootServices. En Windows se puede abrir desde A:. El
informe fijo usa ASCII con valores hexadecimales: bytes del SBEF,
hoja CPUID de cache, lectura del puerto PS/2 64h y cantidad PCI xHCI.
La version 2 agrega BDF, ID PCI y comando PCI de los dos primeros
controladores. La version 3 registra tambien BAR0_LO y BAR0_HI.
El puente lee la configuracion PCI y restaura el selector al terminar.
La mitad alta se lee para un BAR de memoria de 64 bits. Se conserva
el valor bajo crudo para identificar el tipo de BAR. Las filas con
guiones indican posiciones vacias.
El ID contiene dispositivo en los 16 bits altos y fabricante en
los bajos. El bit 1 del comando indica decodificacion MMIO.
Se genera sin teclado ni raton. Un error de escritura permite que
continue el arranque.

La primera captura en metal del 14-11-2026 registro `SBEF=000027D6`,
`CPUID=8000001D`, `PS2=00000055` y `XHCI=00000002`. Windows
identifico los controladores AMD `1022:43BC` y `1022:149C`.

El informe V2 del mismo equipo localiza `1022:43BC` en `03:00.0`
(CMD `0006`) y `1022:149C` en `2B:00.3` (CMD `0007`).
Ambos tienen habilitados MMIO y bus mastering. Windows situa el
teclado HID `1A2C:635A` y el raton HID `4E53:5406` directamente
bajo el concentrador raiz del `149C`, en los puertos 2 y 3 de su
topologia USB. ULTRA-LinuX registra ambos AMD bajo `xhci_hcd` en
`evidencias/audio-juegos/pc-real/PC-configuracion.txt`. BMO-X censa
los puertos antes de elegir el controlador en
`Ultra_kernel_x86-64/kernel/src/ring0/dev/usb/arranque.rs`.

BMO-X2 lee PORTSC de los controladores con MMIO valido y elige
el que tenga mas puertos conectados. La lectura usa el estado
dejado por el firmware. En QEMU, un teclado en el segundo xHCI
abre CABINA mediante F2. La sonda de comandos sigue limitada a
`1B36:000D`. La inicializacion AMD, la enumeracion conjunta y la
entrada sostenida quedan pendientes.

### Condiciones para el siguiente BOOT de entrada

1. Cotejar la base MMIO del AMD `1022:149C` usando el informe V3.
   Ring 0 debe comprobar sus requisitos y registrar la primera fase
   que falle al inicializarlo. V3 registra el estado previo.
2. Cada HID necesita su propia ranura y su cola. Probar coexistencia
   en QEMU y confirmar que la desconexion de uno deja al otro activo.
3. Ring 3 debe mostrar que llegan ambos tipos de evento en CABINA.
   El ensayo debe poder explicar un fallo sin depender del teclado.
4. HOST prepara la imagen FAT32 a partir del perfil probado, conserva
   las huellas y publica el resultado de QEMU antes de probar en metal.

El lanzador ULTRA-J ya prueba Super + Q en QEMU y vuelve al mismo
espacio de trabajo. Este atajo necesita que el kernel entregue las
teclas al escritorio. La prueba del raton USB emulado y la del
teclado USB emulado se ejecutan en perfiles independientes.

El panel ULTRA-J y sus metodos de objeto tienen ensayos propios. El
panel se verifico en QEMU. Las llamadas UJBC v2 se comprobaron en HOST.
El informe UEFI actual identifica el controlador, mientras las fases
de HID posteriores a ExitBootServices requieren su propio registro.

### Estado del controlador

El inventario lee HCSPARAMS2 y HCCPARAMS1 del controlador elegido
para registrar paginas scratchpad y tamano de contexto. Tras
ExitBootServices, `xhci_preflight.inc` lee USBSTS y PAGESIZE a traves
del alias temporal de Ring 0. El escritorio muestra OCUPADO si CNR
esta activo, PAGINA NO ADMISIBLE si el controlador carece de soporte
para 4 KiB, DETENIDO si HCHalted esta activo o ACTIVO en el caso restante.
ACTIVO describe el controlador. Los renglones de teclado y raton
indican por separado si llegaron eventos PS/2.

El perfil habitual deja el semaforo de propiedad del firmware intacto.
El reset, las colas DMA y USB HID pertenecen a la sonda QEMU.
Una foto del aviso en el escritorio complementa BOOTLOG.TXT, que
se escribe antes de ExitBootServices.

La sonda
QEMU usa la secuencia de BMO-X: espera CNR, detiene el controlador,
espera HCHalted, solicita HCRST y comprueba que HCRST y CNR se
borren y que PAGESIZE admita 4 KiB. El estado 3 certifica ese
tramo en QEMU. En el arranque habitual solo se leen los requisitos.
El ensayo de DMA prepara una tabla para hasta cuatro scratchpads y
calcula los desplazamientos segun el tamano de contexto anunciado.
QEMU solicita cero scratchpads y usa contextos de 32 bytes. El
teclado emulado funciona a velocidad completa y alta. Para el AMD
hay que verificar sus capacidades, sus estructuras y el reinicio
con plazos de hardware.

CABINA en Rust muestra los datos de la sesion. Guardar eventos de Ring 0
posteriores a ExitBootServices requiere un controlador de bloques y una
ruta de guardado del sistema. El informe UEFI cubre la fase previa.

El ensayo de escritorio `run-desktop-media-660962069397` conserva los
tres archivos de arranque bajo `media/`, el manifiesto de huellas en
`qemu-results.json` y una captura en `build/puente-normal.png`.
QEMU verifico que la pantalla distingue el inventario xHCI de la
recepcion de eventos PS/2 y que los dos indicadores cambian por separado.

Al entrar por BMO-X2 en UEFI, fotografiar el panel inferior antes de
interactuar. Pulsar F2 y mover el raton, probar un clic y fotografiar
el resultado. Anotar el numero XHCI, los dos estados PS2, si se abrio
CABINA y si se movio el cursor. Incluir el puerto usado y si habia un
hub. Si el arranque se queda en el gato, fotografiar esa pantalla.
El contador XHCI registra controladores PCI detectados. El indicador
PS2 registra eventos recibidos por la ruta PS/2 y puede reflejar la
emulacion del firmware. El transporte USB HID continuo sigue pendiente.
En el equipo, ambos indicadores siguieron esperando con teclado y
raton USB conectados. Tampoco se encendio la iluminacion RGB. El
estado de la iluminacion no identifica la fase de enumeracion.

La sonda `--xhci-command` rearma el endpoint de teclado en QEMU y
coteja 260 informes antes de cerrar CABINA con `session exit`.
Cuatro posiciones de transferencia y dieciseis de eventos se
reutilizan mediante bits de ciclo. El contador de diagnostico
vuelve a cero sin interrumpir la entrada. Al cerrar la sesion se
detiene el controlador y se restaura el comando PCI.
Con `build-desktop.ps1 -Session -External -UsbProbe -AbiRun ...`,
HOST genera `build/desktop/desktop-usb-probe.sbef`. Pasarlo a
`stage_desktop_media.py` con `--xhci-command --usb-desktop` permite
probar la entrega mediante INVOKE. Ring 3 usa el decodificador HID
boot y QEMU verifica que F2 abra CABINA con el controlador activo.
WAIT detecta el informe en un despertar del PIT.

Para la variante de raton, agregar `-UsbMouse` y pasar
`build/desktop/desktop-usb-mouse.sbef` con `--usb-desktop` y
`--usb-mouse`. QEMU comprueba el movimiento en ambos sentidos,
el clic que cambia el foco y la parada tras `session exit`.
La variante usa teclado PS/2 emulado para CABINA.

Ambas sondas quedan en `qemu-only/`. La siguiente prueba requiere
gestionar teclado y raton USB a la vez, retirar y reabrir una ranura
tras desconexion y registrar las fases de enumeracion en metal.

El primer objetivo fisico es llegar a una parada controlada en Ring 0 desde
el firmware UEFI x86-64 y poder explicar en que fase quedo el equipo. El
ensayo de DOOM prueba otra parte del sistema: carga externa, ejecucion CPL3,
framebuffer y teclado en QEMU. Su cargador, mapa de RAM y dispositivos
pertenecen al perfil de la VM.

| Orden | Entrega | Evidencia para avanzar |
|---|---|---|
| 1 | Preparar el EFI y la entrada CASM para un arranque aislado. | Verificar huellas del EFI, del HEX y del paquete; arrancar los mismos bytes en QEMU y conservar el resultado. |
| 2 | Abrir el EFI desde el selector del firmware del equipo. | Registrar placa y version UEFI, modo de arranque, salida de BootServices, entrada CASM y parada observable. Volver a arrancar Windows por su entrada habitual. |
| 3 | Probar los mecanismos de Ring 0 por separado en ese perfil. | Registrar CPU, mapa de RAM, framebuffer y diagnosticos; comprobar pila, excepcion controlada y memoria con permisos. Identificar cada controlador probado. |
| 4 | Arrancar un cliente Rust minimo desde un SBEF externo con el cargador CASM propio. | El kernel mapea RX/R/RW con NX, atiende INVOKE y WAIT y recupera recursos cuando el cliente sale o falla. Repetir con el segundo cliente. |
| 5 | Ampliar al escritorio y los aparatos. | DIRECTOR presenta por CPU y recibe entrada. Disco, audio y otros controladores obtienen evidencia por separado. |

El ensayo puede usar un medio removible o un volumen FAT32 con una ruta
EFI propia. Para este equipo se eligio el volumen A:. La FAT32 dedicada
junto a PERSONAL queda para despues de verificar el recorrido UEFI.

### Ensayo BMO-X2 en el volumen A:

El volumen fijo FAT32 BMO contiene `\EFI\BMO-X2\BMO-X2.EFI` y
`\BMO-X2\INICIO.X86`. El puente derivado conserva sus instrucciones y
cambia tres cadenas UTF-16, incluida la ruta del paquete. OVMF verifica
los tres cuadros de color del gato y HLT en CPL0 con este EFI y paquete.
El run `run-bmo-x2-d296555d2da8` conserva las capturas y el manifiesto.
Se cotejaron las huellas al copiar a A: y las de los EFI de ULTRA.

Desde el explorador de archivos del firmware, seleccionar el volumen BMO
y abrir `\EFI\BMO-X2\BMO-X2.EFI`. Si el firmware ofrece agregar una
opcion, se puede etiquetar BMO-X2 y seleccionar ese archivo. El firmware
puede bloquear el EFI sin firma con Secure Boot activo. El nombre y los
colores de la animacion se ven dentro de BMO-X2; la lista UEFI depende
del firmware. El ensayo fisico sigue pendiente.

Para reproducir la preparacion en el proyecto, ejecutar
`tools/boot/stage_bmo_x2.py` con Python y un run CASM del gato. El script
crea archivos de prueba bajo `build/CASM`.

### Variante de escritorio desde el volumen

`tools/boot/stage_desktop_media.py` toma los runs ABI, gato corto y
escritorio externo. Genera un EFI derivado que abre
`\BMO-X2\DESKTOP.SBF` antes de ExitBootServices y entrega su direccion y
longitud al validador de la sonda. Conserva un arranque con el gato y
permite comprobar en QEMU la entrada CPL3, F2 y el rechazo de W+X sin
depositar el SBEF con el cargador de QEMU.

El escritorio de prueba usa framebuffer GOP y entrada PS/2. En el equipo
se debe comprobar la presentacion y F2 por separado. El medio de prueba
de escritorio incluye el SBEF Rust y tres archivos en total. DOOM con
IWAD y el cargador CASM de produccion quedan pendientes.

El run `run-desktop-media-65a35111cc51` aprobo los dos casos en QEMU con
1024 MiB. Sus tres archivos se copiaron a las carpetas BMO-X2 de A:
y se cotejaron sus huellas. El arranque anterior del gato se conserva
en `previous-splash` dentro del run. Seleccionar la entrada UEFI BMO-X2
y pulsar F2 al aparecer el escritorio.

El propietario confirmo que el escritorio aparece en el equipo y que
teclado y raton quedan sin respuesta. El inventario de Windows identifica
ambos como USB HID y dos controladores AMD xHCI. BMO-X divide ese camino
entre el controlador xHCI, la enumeracion USB y la decodificacion HID.
ULTRA-LinuX usa `xhci_hcd` y la capa HID del kernel Linux en su perfil PC.

El ensayo de BMO-X2 incorpora un inventario PCI xHCI de solo lectura
con aviso visible en Ring 3. Detectar la clase PCI no habilita USB.
El inventario registra el BDF y los BAR del primer controlador.
La sonda Ring 0 comprueba la habilitacion PCI y la direccion del BAR
antes de instalar un alias temporal de 4 KiB de solo lectura, supervisor
y NX. Lee CAPLENGTH, HCIVERSION y HCSPARAMS1, retira el alias e invalida
su TLB. QEMU coteja BDF, BAR y registros con su monitor y verifica que
las entradas de pagina queden en cero. Evidencia en el run
`run-desktop-media-dc3616a211e3`. El ensayo se conserva en el proyecto.
El escritorio Rust ya traduce informes HID boot en pruebas HOST. Mantiene
flancos y modificadores del teclado, deltas y botones del raton, y libera
el estado al desconectar. Faltan el transporte xHCI, memoria DMA concedida
por Ring 0, transferencias con plazo y su entrega a este decodificador.
La prueba de cierre debe
inyectar eventos por dispositivos USB en QEMU y luego repetir F2 y
movimiento del puntero en el equipo.

La sonda recorre las capacidades extendidas dentro de la pagina MMIO.
Si encuentra USB Legacy Support, solicita la propiedad y limita el sondeo
a 100000 lecturas. Si el firmware conserva su propiedad, revierte la
peticion y registra el vencimiento. Este paso no activa DMA ni reinicia
el controlador.

El run `run-desktop-media-95951adfa9e3` aprobo el arranque y el rechazo
de W+X. El controlador emulado no expone USB Legacy Support, asi que la
prueba observo el estado 1. La cesion efectiva y el vencimiento quedan
por comprobar. El paquete de arranque ocupa 4002 de los 4096 bytes
aceptados por el puente. El transporte completo necesita una etapa
separada del paquete inicial.

Orden de cierre de xHCI: validar y mapear toda la ventana operativa de
cada controlador, verificar el traspaso en el equipo y deshabilitar los
SMI de legado tras obtener propiedad. Luego reservar memoria DMA de las
colas y activar el controlador. Despues enumerar los
perifericos, seleccionar HID boot y entregar transferencias de teclado
y raton al decodificador Rust. BMO-X aporta la referencia del traspaso,
los anillos y la reutilizacion de paginas. Medir memoria, latencia y
actividad en reposo cuando haya informes USB reales.

Por cada prueba guardar huellas, configuracion, bytes de entrada, memoria
reservada y el ultimo punto observado. Registrar consola serie si el
equipo la ofrece, o captura del diagnostico visible. Faggin mantiene su
[ruta propia desde reset](../contracts/FAGGIN.md), con la misma entrega
CASM como destino.

| Referencia | Responsabilidad en BMO-X2 |
|---|---|
| TALK-CPU | Puente inicial, entrega de CPU y modelo de etapas Faggin. |
| BMO-X | Lecciones de aislamiento, capacidades y diagnostico. Base de los componentes Rust que se revisen para Ring 3. |
| Ultra-LinuX | Experiencia de escritorio, especialmente espacios y foco, y disciplina de verificacion de builds. |

Los contratos, los artefactos verificados y las pruebas del equipo se
registran en BMO-X2. [Procedencia](../heritage/TRANSFER.md) y
[orden de cierre de Ring 0](RING0-PLAN.md).

## Hitos de la entrada

La base del kernel se escribe desde cero en CASM. BMO-X aporta lecciones y
contratos de referencia; no se ha copiado su kernel Rust a este arbol.

### M0: emision comprobable en el anfitrion

`kernel/boot/entry.casm` es la primera fuente nueva del kernel. Es una sonda
pequena del perfil metal64: imprime un mensaje mediante la tabla de servicios
del cargador y retorna. No configura CPU, memoria o interrupciones.

```powershell
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
```

La orden congela la fuente, produce HEX e IR y ejecuta el verificador antes de
publicar el paquete. Su resultado acredita emision HOST, no una entrada ejecutada
en Ring 0. `metal_puts` requiere la tabla de servicios R15 del contrato metal64;
un salto directo a esos bytes no satisface ese contrato.

### M1: el primer arranque en QEMU

Genesis G1 paso siete casos QEMU/OVMF el 05-11-2026: ejecucion normal con
salida de BootServices, copia exacta del cuerpo, framebuffer esperado, retorno
y CPL=0/HLT=1; cinco rechazos de archivo/paquete y un MapKey invalido con tres
reintentos acotados. Evidencia en `kernel/boot/genesis/evidence/`.
Reproducir con `bmo-x2.ps1 -Accion despertar`.

TALK-CPU ofrece el puente de referencia y evidencia historica de su contexto.
La revision de piezas y condiciones esta en [TRANSFER](../heritage/TRANSFER.md).
La repeticion con Genesis es una prueba nueva conservada aqui; los resultados
anteriores de TALK-CPU no se suman como evidencia del hijo.

1. Fijar la cadena de carga y su contexto: modo de CPU, mapa de memoria,
   framebuffer, pila, tablas de servicios y tratamiento del retorno.
2. Cargar una imagen admitida y llegar a la entrada CASM con ese contexto.
3. Observar el mensaje de diagnostico y una parada controlada del invitado.
4. Rechazar un contexto o imagen incorrectos con un motivo observable.

Antes de llamarlo kernel autonomo, sustituir los servicios provisionales del
cargador por mecanismos propios con sus contratos y pruebas.

### Presupuesto de la entrada Ring 0

La entrada minima propia vive en [kernel/boot/stop](../kernel/boot/stop/README.md).
CASM emite el cuerpo x86-64 en `program.hex` y su IR en `program.ir.json`.
El verificador reconstruye los bytes y aplica el limite antes de publicar
`INICIO.X86`. El limite es estricto, con un maximo de 511 bytes para
el paquete. La cabecera de 24 bytes deja hasta 487 para codigo y datos.
La entrada actual usa 4 bytes de cuerpo y 28 de paquete, con 483 de margen.

El puente UEFI heredado de 12288 bytes pertenece a la cadena de carga.
El presupuesto mide el paquete binario de la entrada, mientras que
`HEX.md` registra aparte el tamano de la representacion de texto.
Las etapas posteriores del kernel tendran su propio presupuesto.

### M2: excepciones y aislamiento

CPU y excepciones primero; despues paginas y permisos. Un #UD controlado debe
dar diagnostico. Mas adelante, el primer programa Rust en Ring 3 pide una
operacion y recibe una respuesta; su fallo termina ese proceso.

Tiempo, planificacion, IPC y drivers tienen nodos reservados con criterios de
aceptacion. Se implementan cuando este recorrido minimo los requiera.

La inspiracion Linux se aplica a separar `arch`, `mm`, `sched`, `ipc` y los
drivers en una estructura navegable. Las decisiones de ABI, capacidades y CASM
siguen siendo propias de BMO-X2. Un solo repositorio combina las piezas y
conserva sus fronteras de privilegio.
