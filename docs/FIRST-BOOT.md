# Primer hito: una entrada propia y un fallo explicado

## Primera prueba en hardware

### Diagnostico visible de teclado y raton

El puente UEFI escribe `\BMO-X2\BOOTLOG.TXT` en el volumen de arranque
antes de ExitBootServices. En Windows se puede abrir desde A:. El
informe fijo usa ASCII con valores hexadecimales: bytes del SBEF,
hoja CPUID de cache, lectura del puerto PS/2 64h y cantidad PCI xHCI.
La version 2 agrega BDF, ID PCI y comando PCI de los dos primeros
controladores. Las filas con guiones indican posiciones vacias.
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

El inventario lee HCSPARAMS2 y HCCPARAMS1 del controlador elegido
para registrar paginas scratchpad y tamano de contexto. La sonda
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
coteja tres informes consecutivos: F2 pulsada, F2 liberada y F3
pulsada. Al terminar detiene el controlador y restaura el comando PCI.
Con `build-desktop.ps1 -Session -External -UsbProbe -AbiRun ...`,
HOST genera `build/desktop/desktop-usb-probe.sbef`. Pasarlo a
`stage_desktop_media.py` con `--xhci-command --usb-desktop` permite
probar la entrega de los tres informes mediante INVOKE. Ring 3 usa
el decodificador HID boot y QEMU verifica que F2 abra CABINA. La
sonda queda en `qemu-only/`. Faltan colas reutilizables con el
controlador activo, WAIT para USB, raton y validacion en metal.

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
