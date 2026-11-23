# Candidato de escritorio RmlUi desde FAT32

El candidato une el motor RmlUi/FreeType, el dibujo Rust y la politica
DIRECTOR existente de Rust. Es un panel ULTRA-J con espacios y cierre,
no la migracion completa de CABINA, DOOM y todas las aplicaciones.
El arranque anterior se conserva para esas funciones.

## Que esta comprobado

- QEMU arranca el gato compacto CASM y lee el SBEF desde FAT32 mediante
  UEFI. No se inyecta un modulo con `-device loader`.
- Antes de ExitBootServices se reserva el rango privado de usuario en
  04000000h, con 16 MiB en el perfil base y 18 MiB en Full HD nativo.
  El cargador comprueba esa reserva y el mapa antes de escribir alli.
- El lector tiene un perfil explicito de hasta 2 MiB. El limite de
  16,512 bytes del escritorio anterior no se amplia silenciosamente.
- El archivo INICIO.X86 sigue cabiendo en la pagina de 4 KiB. Se utiliza
  el gato compacto, porque el HD y esta entrada excederian ese limite.
- DIRECTOR decide foco, espacios, movimiento y cierre. La superficie
  1x1 que usa su adaptador es solo un marcador de politica: no comparte
  como referencia Rust el framebuffer mutable propiedad de C++.
- El presentador base acepta la superficie logica 1280x800. En GOP menores
  usa una vista 640x400; en los mayores usa escala entera y centrado.
  QEMU verifica los pixeles del camino normal y del GOP 1024x768.
- Se prueban Enter, clic PS/2, espacios, cierre, reapertura y rechazo
  W+X antes de copiar codigo. Se vuelve a leer el BOOTLOG de la imagen
  FAT32 y se compara el SBEF del disco con el ejecutable esperado.

El heap sigue acotado a 4 MiB. En el candidato base, el framebuffer ocupa
4,096,000 bytes y el SBEF mide 1,845,846 bytes. El pico medido de su heap es
3,050,544 bytes. Las pruebas y huellas quedan conservadas en
[la evidencia del candidato](../Ultra-J/evidence/rmlui-desktop-fat32.json).
El mapeo privado incluye la pila del escritorio. El nano-core lleva
su propia contabilidad de memoria.

## Prueba fisica preparada

En esta maquina ya se registro una entrada separada del firmware llamada
**BMO-X2 Desktop (RmlUi)**. Elegir ese nombre en el menu de arranque.
Tras la confirmacion de METAL del propietario se retiro la entrada
antigua **BMO-X2** del firmware. Sus cuatro archivos se archivaron con
SHA256 en `build/archives/retired-bmo-x2` y se retiraron de A: por pedido
del propietario. Linux/ULTRA y los otros arranques quedan fuera de esa limpieza.
Los archivos visibles en el Explorador no son entradas del menu UEFI.

En el volumen FAT32 BMO (A: bajo Windows), abrir desde el selector de
archivos del firmware UEFI:

```text
\EFI\BMO-X2\DESKTOP.EFI
```

El programa lee exclusivamente:

```text
\BMO-X2\DESKTOP\INICIO.X86
\BMO-X2\DESKTOP\DESKTOP.SBF
```

El despliegue del candidato nuevo no cambia
NVRAM, orden de arranque, particiones ni el cargador de Windows.
`DEPLOY.JSON` identifica los hashes copiados y los originales conservados.

La distribucion activa queda asi; las actualizaciones sobreescriben estas
mismas rutas y los respaldos van al proyecto:

```text
A:/EFI/BMO-X2/DESKTOP.EFI
A:/BMO-X2/DESKTOP/INICIO.X86
A:/BMO-X2/DESKTOP/DESKTOP.SBF
A:/BMO-X2/DESKTOP/DEPLOY.JSON
A:/BMO-X2/DESKTOP/BOOTLOG.TXT
```

`native/retire-legacy.ps1` solo retira los cuatro archivos exactos del
perfil anterior, tras comprobar la entrada nueva y todas sus huellas.
Archiva y verifica todos los originales antes de borrar el primero.
No hace una limpieza general de EFI ni usa borrados recursivos.

El registro opcional se hace por separado con
`tools/desktop/rmlui/native/register-desktop.ps1`, en PowerShell elevado.
Comprueba los tres hashes del candidato, reutiliza una entrada compatible
o crea una nueva al final de la lista. No selecciona el siguiente arranque
ni reinicia. Su recibo queda en `build/rmlui-native/firmware-desktop.json`.

El firmware debe ejecutar el EFI x86-64 propio; el procedimiento no cambia
la politica de Secure Boot. Si el firmware no ofrece abrir archivos,
hay que usar su selector/shell o preparar una entrada separada.

### Controles del candidato

| Entrada | Resultado |
| --- | --- |
| Ctrl+Super+1..4 | Cambiar espacio |
| Super+1..9 | Enfocar el numero de ventana dentro del espacio |
| Super+Shift+1..4 | Mover el panel al espacio elegido |
| Super+Q | Cerrar el panel enfocado; la base permanece |
| F1 o Abrir ULTRA-J | Abrir o traer el panel al espacio actual |
| Enter o boton Activar ULTRA-J | Ejecutar UJBC nativo si el panel esta activo |

Cerrar el panel retira su identidad de DIRECTOR; la base conserva el
documento/atlas para reabrirlo. No es todavia descarga completa de un
proceso SBEF ni liberacion del mapeo de usuario.

## Evidencia y limites en metal

El 16-11-2026 el propietario confirmo la presentacion de RmlUi en METAL
con fotografia y BOOTLOG PRE-EBS, GOP 1920x1080. Ver
[evidencia del arranque fisico](../Reports/rmlui-desktop-metal-20261116.json).
Esto acredita lectura UEFI y llegada visual a Ring 3, no entrada USB.

USB HID sigue pendiente: la ruta AMD existente lee descriptores, pero
faltan configuracion de interfaces/endpoints interrupt y entrega de
informes de teclado y raton. El candidato usa entrada PS/2; que funcione
en QEMU no acredita esos USB fisicos. La luz RGB tampoco acredita HID.

El candidato escribe, antes de salir de UEFI:

```text
A:\BMO-X2\DESKTOP\BOOTLOG.TXT
```

El encabezado es `BMO-X2 DESKTOP UEFI PRE-EBS`. Incluye tamano SBEF,
GOP_WIDTH/GOP_HEIGHT, CPUID, PS2 y controladores PCI xHCI. Es evidencia
de lectura/preparacion UEFI, no un registro en vivo de Ring 0/Ring 3.
Cada candidato nuevo sigue necesitando su propio archivo y fotografia
del escritorio o del error para acreditar el arranque fisico.

La nueva variante de presentacion deja el gato CASM como saludo visual,
sin el texto de exito METAL64/BootServices ni el mensaje de carga UEFI.
Se preservan las firmas internas del contexto, las rutas de error y los
diagnosticos de BOOTLOG; el nombre visible no cambia el contrato binario.

CHKDSK A: en solo lectura no encontro problemas. Eso comprueba la
estructura del FAT32 montado; no es un ensayo de superficie con /R,
ni una prueba de los drivers del sistema propio.

## Ruta grafica base: CPU y framebuffer de UEFI

BMO-X2 toma del GOP el modo y la direccion del framebuffer lineal.
Despues de `ExitBootServices`, Ring 3 dibuja en CPU y presenta por la
capacidad de pantalla. El presentador usa el framebuffer entregado
por el firmware. La ruta base funciona sin instalar el driver NVIDIA
del sistema operativo ni arrancar el GSP para aceleracion 3D.
[Entrega del framebuffer segun TianoCore](https://github.com/tianocore-docs/edk2-UefiDriverWritersGuide/blob/main/23_graphics_driver_design_guidelines/232_graphics_output_protocol_implementation/2324_querymode%2C_setmode%2C_and_blt_implementation.md).

La foto y el BOOTLOG de METAL acreditan imagen a 1920x1080 en el equipo
del autor. Ese registro no identifica el dispositivo PCI propietario
del GOP. Se conserva el modo fijado al arrancar. La ruta base carece
de cambio de modo en sesion, page flip, VRR y aceleracion 3D. Una futura
ruta de aceleracion sera un backend separado con evidencia propia.

HOST construye el perfil `cpu-gop` con PS/2 por defecto y admite xHCI
como opcion de entrada. El puente nativo copia el [modulo de
pantalla](../kernel/drivers/display/GOP/gop_stage.inc) a una pagina
supervisora ya reservada dentro de su contexto. INVOKE 9 copia el cuadro
completo e INVOKE 10 actualiza el cursor y la franja de estado en escala 1.
En los demas modos el cliente usa INVOKE 9 para la presentacion.
DIRECTOR, RmlUi y ULTRA-J usan la misma capacidad de pantalla. Un futuro
backend de GPU debe poder retirarse del build conservando la ruta
`cpu-gop` y los perfiles de entrada.

El ensayo `run-rmlui-media-68bf3ec46327` verifica pantalla, cursor y
accion ULTRA-J con PS/2 y sin reserva DMA de xHCI. Dos movimientos del
cursor copiaron 816 pixeles sin volver a rasterizar el escritorio. Su
`INICIO.X86` ocupa 3609 B. La comprobacion de permisos SBEF rechazo W+X
antes de copiar el codigo de usuario.
El ensayo `run-rmlui-media-d067649498bb` comprobo los mismos 816 pixeles
con teclado y raton USB simultaneos y verifico la revocacion del acceso
del controlador USB al detenerlo. Su `INICIO.X86` ocupa 3947 B.
El ensayo `run-rmlui-media-0110f5161574` verifico GOP 1024x768 con
presentacion de cuadro completo a 640x400 cuando la copia por regiones
queda fuera de la escala admitida.

Las referencias de los otros proyectos explican dos decisiones:

- [ULTRA-LinuX W2](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/docs/WAYLAND.md#w2-la-primera-ventana)
  mostro Cage y Foot con Pixman por CPU sobre simpledrm. El perfil PC
  acelerado usa otra pila con modulos NVIDIA, firmware GSP y componentes
  de usuario.
- [BMO-X](https://github.com/AndreeSalazar/BMO-X-x86-64/blob/6076bdefefc67877419ca53633c6e40cb45fc92d/docs/identidad/LA_RAM.md#el-escalon-8-y-por-que-faltaba-de-esta-tabla-2026-08-12)
  redujo copias de su escritorio con regiones modificadas sobre GOP.
  Su [ruta acelerada RTX 3060](https://github.com/AndreeSalazar/BMO-X-x86-64/blob/6076bdefefc67877419ca53633c6e40cb45fc92d/README.md#verrano)
  demostro rasterizado en GPU y aun registra arranques del GSP fallidos.

### GPU / NVIDIA

El perfil `--nvidia-probe` agrega una [sonda PCI](../kernel/drivers/GPU/NVIDIA/pci_probe.inc)
al puente UEFI. BMO-X2 lee directamente la configuracion PCI del
segmento 0 antes de cerrar Boot Services. Registra cuantas funciones
graficas aparecen y cuantas llevan el identificador NVIDIA `10DE`.
Si hay una coincidencia, registra el BDF de 16 bits, el par de
dispositivo y proveedor, y el valor observado de PCI Command.
Con PCI clasico, `BDF = bus << 8 | dispositivo << 3 | funcion`; en
`GPU_NVIDIA_ID` el proveedor ocupa los 16 bits bajos.

El inventario ampliado registra `GPU_RES_BDF`, `GPU_BARS` y
`GPU_SUBSYS`. Lee las seis palabras BAR y el identificador de subsistema
de un dispositivo de pantalla con cabecera PCI tipo 0. Da prioridad a
la primera funcion NVIDIA. Los BAR de 64 bits ocupan dos palabras.
Esta lectura conserva las asignaciones del firmware y no mide la
longitud de los BAR ni la VRAM. Los BAR no se mapean ni se prueban con
escrituras. QEMU compara el BDF y las direcciones de BAR de su VGA con QMP.

El candidato usa `\EFI\BMO-X2\NVIDIA.EFI` y sus propios `INICIO.X86` y
`DESKTOP.SBF` en `\BMO-X2\GPU\`. El reporte queda en
`\BMO-X2\GPU\GPULOG.TXT`. Los valores `--------` indican ausencia de
una funcion NVIDIA. La sonda restaura el selector PCI, solo lee datos
de configuracion y termina en UEFI. El perfil usa el mismo presentador
`cpu-gop` y el mismo ABI de Ring 3.

ULTRA-LinuX exige evidencia separada para identificar la tarjeta,
inicializar el driver y confirmar que el compositor usa la GPU. BMO-X2
adopta esa secuencia y usa el inventario de ULTRA-LinuX como referencia
del equipo. Su pila combina modulos del kernel Linux, firmware GSP y
componentes NVIDIA de una misma version. Aprovechar esa referencia en
BMO-X2 requiere adaptar la inicializacion a sus propias interfaces de
PCI, memoria y DMA. La aceleracion exige una inicializacion fiable y
un trabajo verificable de GPU en un buffer propio, antes de conectar
RmlUi. El caso GSP `0x15` de BMO-X sigue siendo una referencia de fallo.
[Arranque NVIDIA de ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/docs/HYPRLAND-W3C.md).
El ensayo W3h en METAL confirma DRM, GL 3.2 y HDMI a 1920x1080/60 Hz
en Hyprland sobre la misma RTX con firmware `615.78.08`. Es una
referencia de version y de prueba, no un requisito de instalacion para
el inventario BMO-X2. [Evidencia W3h](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/docs/PC-REAL-W3H.md).
[Capas del driver NVIDIA](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/README.md#directory-structure-layout).

En el registro del equipo del autor, ULTRA-LinuX encontro
`10de:2504` en `0000:29:00.0`. En BMO-X2 el par apareceria como
`GPU_NVIDIA_ID=250410DE`. Con la misma enumeracion de buses,
`GPU_NVIDIA_BDF=00002900`. El BDF puede variar segun el firmware.
[Registro PCI de METAL](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/evidencias/pc-real/nvidia-2026-10-19/dmesg-pc.txt#L414).

La primera prueba BMO-X2 en METAL del 20-11-2026 obtuvo ambos valores y
mostro el escritorio con GOP a 1920x1080. PCI Command era `0003` antes de
ExitBootServices, con decodificacion de memoria y sin bus mastering.
[Informe de METAL](../Reports/nvidia-pci-metal-20261120.json).

El segundo arranque de METAL capturo los BAR de la RTX `10DE:2504`
con subsistema `1462:397D`. Sus cuatro bases coinciden con el
inventario de ULTRA-LinuX para `0000:29:00.0`. Los tamanos de esta tabla
son la referencia de ULTRA-LinuX. BMO-X2 leyo las bases en la
configuracion PCI anterior a ExitBootServices.

| BAR | Base observada en BMO-X2 | Longitud informada por ULTRA-LinuX |
| --- | --- | --- |
| 0 (memoria de 32 bits) | `0xFB000000` | 16 MiB |
| 1 (memoria de 64 bits) | `0xD0000000` | 256 MiB |
| 3 (memoria de 64 bits) | `0xE0000000` | 32 MiB |
| 5 (puertos de E/S) | `0xE000` | 128 B |

[Segundo informe de METAL](../Reports/nvidia-pci-metal-20261120-bars.json).
[Rangos PCI de ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/evidencias/pc-real/nvidia-2026-10-19/dmesg-pc.txt#L414-L418).

El arranque de BMO-X2 conserva la pantalla configurada por UEFI y
llega al escritorio con CPU + GOP. El inventario
PCI es de solo lectura. BMO-X llego mas lejos con VERRANO: ejecuto
trabajo en la RTX y comprobo rasterizado. Su fallo intermitente
`MAILBOX0=0x15` ocurrio durante la inicializacion del GSP. La evidencia
disponible no atribuye ese fallo a Rust. La comparacion equivalente
empieza cuando ambos sistemas ejecutan trabajo en la GPU.
[Investigacion GSP de BMO-X](https://github.com/AndreeSalazar/BMO-X-x86-64/blob/6076bdefefc67877419ca53633c6e40cb45fc92d/README.md#case-file-the-booter-that-said-no-0x15).

La [sonda MMIO](../kernel/drivers/GPU/NVIDIA/mmio_probe.inc) pide al
firmware los limites de BAR0 via `EFI_PCI_IO_PROTOCOL.GetBarAttributes`
y coteja su base con el inventario PCI. Para la RTX `10DE:2504` lee un
registro de identidad con la ventana MMIO acotada y verifica PCI Command.
La inicializacion posterior debe acreditar una version GSP compatible y
recursos PCI y DMA acotados. El primer trabajo acelerado debe dejar un
resultado verificable en un buffer propio antes de cambiar el presentador
de RmlUi. El perfil NVIDIA conserva CPU + GOP durante estos ensayos.
[Referencia EDK II](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Bus/Pci/PciBusDxe/PciIo.c).

#### Secuencia comprobada en ULTRA-LinuX y aplicacion en BMO-X2

| Etapa en ULTRA-LinuX | Aplicacion en BMO-X2 |
| --- | --- |
| El perfil PC compila `nvidia-open` contra su propio kernel, verifica `vermagic` y empaqueta `nvidia-utils` de la misma version. El perfil generico conserva la ruta por software. | Mantener el ensayo NVIDIA aislado de CPU + GOP. Para la fase GSP, fijar y verificar una combinacion de firmware y protocolo del controlador con procedencia documentada. `615.78.08` es la referencia comprobada en ese PC. |
| La sesion NVIDIA exige un dispositivo DRM cuyo driver sea NVIDIA, verifica que el proveedor EGL exista y prepara los tres nodos GPU, control y modeset. | Comprobar primero el dispositivo por segmento/BDF e identidad PCI. Separar las pruebas de inventario, lectura de registros e inicializacion. Cada una informa su propio resultado. |
| Hyprland recibe la tarjeta DRM seleccionada. La sesion corre sin privilegios adicionales y exporta modo, renderer y salida de la prueba. | Conceder recursos graficos al backend solo despues de una tarea GPU de resultado verificable. DIRECTOR/RmlUi consume la capacidad de presentacion. Informar la fase exacta alcanzada aunque el ensayo falle. |

[Compilacion PC en ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/scripts/build-baseline.sh#L159-L187).
[Preparacion de la sesion](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/src/rootfs/bin/ultra-sesion#L72-L95).
[Preparacion de nodos NVIDIA](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/src/rootfs/bin/ultra-preparar-nvidia).

La sonda resuelve el protocolo por segmento/BDF, valida el descriptor
de memoria y registra `GPU_BAR0_LEN`. Solo el dispositivo `10DE:2504`
con memoria habilitada y bus mastering apagado llega a `Mem.Read`
(BAR0, desplazamiento cero, un valor de 32 bits). La sonda confirma que
PCI Command conserve su valor y exige que `NV_PMC_BOOT_0` identifique
GA106 (`0x176`). Libera los buffers de UEFI y deja continuar GOP.

| `GPU_MMIO_STATUS` (hex) | Resultado |
| --- | --- |
| `00` | Sin funcion de pantalla seleccionada |
| `01` | Sin protocolo PCI I/O para el BDF |
| `02` | BAR0 asignado o descriptor UEFI no admitido |
| `03` | BAR0 validado en otro dispositivo. Lectura NVIDIA omitida |
| `04` | Lectura de configuracion o estado de PCI Command no admitido |
| `05` | UEFI no pudo leer el registro |
| `06` | Valor de `GPU_PMC_BOOT0` incompatible con GA106 |
| `07` | PCI Command cambiado o no verificable despues de la lectura |
| `08` | Lectura valida de GA106 |

La lectura valida acredita acceso MMIO. GSP y la ejecucion de trabajo
GPU requieren sus propias pruebas.
[Registro de identificacion en NVIDIA](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/inc/swref/published/nv_ref.h).

#### Reserva y lectura de la tabla DTE

El perfil QEMU `--amdvi-dte-reserve` reserva 512 paginas (2 MiB) en UEFI
y comprueba las 262,144 palabras iniciales en cero. Tras
`ExitBootServices`, Ring 0 vuelve a comprobar que el mapa EFI conserva
todo el rango como `EfiLoaderData`; lo lee mediante un alias CPU
supervisor de solo lectura y NX, verifica las 262,144 palabras y revoca
el alias antes de reutilizar la tabla temporal para xHCI. Ring 3 muestra
`AMDVI_DTE_POST=01 00040000` cuando completa esa prueba.

```powershell
$py = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py -B tools/desktop/rmlui/native/guest.py --desktop --usb both --amdvi-post --amdvi-dte-report
& $py -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --amdvi-probe --amdvi-post --amdvi-dte-reserve
```

El perfil es de laboratorio QEMU y no genera medio instalable. La reserva
UEFI y su lectura post-EBS son un ensayo separado. La siguiente ejecucion
QEMU construyo una tabla de 512 paginas (2 MiB) con 65,536 DTE: las
entradas sin dominio apuntan a una raiz vacia de denegacion, EDU, xHCI y
AHCI reciben dominios independientes, se invalidan los 12 solicitantes
presentes y la prueba confirma DMA traducido, rechazo fuera de rango,
revocacion y continuidad de HID. Pasaron los tres casos QEMU: normal,
rechazo W+X y AMD-Vi ausente.
[Evidencia de tabla DTE completa](../Reports/amdvi-full-dte-default-deny-qemu-20261121.json).

Esto solo valida dispositivos virtuales. AMD-Vi fisico sigue apagado; la RTX
no recibio DMA y este ensayo no prueba GSP ni dibujo 3D. El siguiente umbral
es preparar la misma politica de denegacion desde la topologia IVRS y el
censo PCI fisicos, incluyendo puentes y funciones hermanas; identificar
cada bus master, detenerlo o darle un dominio acotado, y revisar la tabla
antes de habilitar traduccion en METAL. Despues se puede probar una
concesion y revocacion de la RTX sin presentar el resultado como aceleracion
hasta verificar el inicio del GSP y un render escrito por la GPU.
[Reporte post-EBS](../Reports/amdvi-dte-post-ebs-qemu-20261121.json).

#### Preflight METAL aislado (sin DMA)

El panel optativo de Ring 3 se agrega con `--rtx-lab-panel` en
`guest.py` y `media.py`. F4 abre y cierra el estado de la prueba RTX.
Muestra la captura AMD-Vi y la preparacion del firmware junto con los
cuatro resultados pendientes: USB traducido, DMA limitado de la RTX,
respuesta del GSP y primer triangulo. F2 conserva el inventario PCI.
El panel se incluye solo en la variante de prueba y abrirlo no cambia
el estado de los dispositivos.

`--metal-amdvi-preflight` genera un candidato aparte para capturar el inventario
NVIDIA/AMD-Vi y verificar que la reserva DTE de 2 MiB sobrevive a
`ExitBootServices`. La sonda observa la traduccion AMD-Vi y el bit de bus
master de la RTX sin modificarlos. No inicia GSP ni trabajo 3D. No incluye censo DMA ni
sondas de almacenamiento en este primer arranque para respetar los slots
verificados de Ring 0.

La compilacion alarga el lector de 4 a 8 KiB y desplaza xHCI y la sonda AMD-Vi
a sus propias paginas; el informe cabe en la ventana reservada `0xc00-0x1000`.
El candidato usa `BMO-X2/GPU-PF` y `EFI/BMO-X2/AMDVI-PREFLIGHT.EFI`, por lo
que no sustituye `NVIDIA.EFI`, `GPU/INICIO.X86`, `GPU/DESKTOP.SBF` ni el
`GPU/GPULOG.TXT` que ya tienes.

```powershell
$py = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py -B tools/desktop/rmlui/native/guest.py --desktop --usb both --amdvi-post --amdvi-dte-report
& $py -B tools/desktop/rmlui/native/media.py build/CASM/run-20261117-215023-ba7dd515 build/CASM/run-20261112-044806-6da064f6 --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-dte-reserve --metal-amdvi-preflight
```

La ejecucion de QEMU del 21-11-2026 paso 3/3: arranque FAT32, rechazo de
SBEF W+X y verificacion post-EBS de la tabla DTE. Eso solo valida el candidato
virtual. Para el ensayo fisico copia los tres archivos de `media` conservando
sus rutas y arranca `AMDVI-PREFLIGHT.EFI` desde el selector UEFI de archivo;
no reemplaces entradas ni archivos existentes. El informe nuevo queda en
`A:\BMO-X2\GPU-PF\GPULOG.TXT` y recoge el estado anterior a ExitBootServices.
Fotografia tambien el pie del escritorio con `AMDVI_DTE_POST` para conservar
el resultado posterior a ExitBootServices. Aun despues de ese ensayo la RTX no tendra DMA,
GSP ni aceleracion 3D: se necesita cerrar primero el mapa fisico por requester,
aplicar dominios e invalidaciones tras detener los dispositivos que corresponda y probar una concesion
y revocacion acotadas antes de mandar trabajo a la GPU.
[Resultado QEMU registrado](../Reports/amdvi-metal-preflight-qemu-20261121.json).

El arranque METAL del 22-11-2026 confirmo la reserva UEFI de 512 paginas a
partir de `0xB7CE2000`, con las 262,144 palabras de 64 bits en cero. En esa
captura la tabla de dispositivos de AMD-Vi era cero, la traduccion estaba
desactivada y la RTX `29:00.0` tenia PCI Command `0003` (Bus Master apagado).
El archivo termina antes de ExitBootServices. La vista del escritorio muestra
`AMDVI_DTE_POST` con el codigo y el motivo, incluso si se omite o falla la
lectura. El resultado esperado es `01 00040000`.
[Registro METAL](../Reports/amdvi-preflight-metal-20261122.txt).

Una foto del escritorio METAL del mismo dia confirma
`AMDVI_DTE_POST=01 00040000`: Ring 0 leyo la reserva completa despues de
ExitBootServices y verifico la retirada del alias temporal de CPU. En la
misma captura, el registro de base de la tabla AMD-Vi seguia en cero.
Queda pendiente verificar el dominio DMA de la RTX con el censo fisico,
incluidas las funciones hermanas y los dispositivos que ya tienen DMA.
La primera prueba NVIDIA debe comprobar la concesion y la revocacion
del DMA acotado antes de avanzar a la respuesta del GSP y al dibujo 3D.

El HOST puede cruzar el mismo censo con el dmesg de ULTRA-LinuX usando
`ivrs.py --census-json ... --linux-pci-log ...`. En esa captura, NVIDIA
`29:00.0` y su audio HDMI `29:00.1` comparten el grupo 16. El segundo
xHCI `03:00.0` comparte el grupo 15 con SATA, Ethernet y puentes PCI.
El censo BMO-X2 no aporta PCI Command para `00:14.0`, `25:00.0` ni
`29:00.1`. Hay que leer esas funciones en el mismo arranque y validar
la parada o el dominio de los dispositivos activos. Los grupos de Linux
quedan como referencia historica, sin conceder DMA en BMO-X2.
[Cotejo de grupos PCI](../Reports/amdvi-linux-group-reference-20261122.json).

El preflight registra `DMA_PCI_00A0`, `DMA_PCI_2500` y `DMA_PCI_2901`
para SMBus, Ethernet y audio HDMI. Cada linea contiene el ID PCI
(dispositivo en la mitad alta, fabricante en la mitad baja) y PCI
Command. La mascara `0004` de Command indica Bus Master Enable.
Una funcion ausente aparece con guiones; `DMA_PCI_0000` sirve de control
con el puente anfitrion. Estas lecturas son previas a ExitBootServices:
registran el estado heredado y complementan el censo posterior a USB.

El registro METAL del 22-11-2026 a las 20:39 confirmo las tres identidades
del cotejo Linux y Bus Master apagado antes de ExitBootServices:
SMBus `1022:790b` con Command `0403`, Ethernet `10ec:8168` con
`0000` y audio HDMI `10de:228e` con `0000`. La RTX mantuvo
`0003`. En cambio, los dos xHCI seguian con Bus Master habilitado
(`0006` y `0007`). La foto del mismo arranque conserva el resultado
`AMDVI_DTE_POST=01 00040000`. Queda verificar el estado de todos estos
dispositivos despues de iniciar USB y transferir o detener cada motor
activo antes de habilitar traduccion fisica.
[Registro METAL del inventario ampliado](../Reports/amdvi-dma-peers-metal-20261122.txt).

El ensayo `run-rmlui-media-4910a511a24c` verifica en QEMU el descriptor
UEFI de la VGA, su longitud de 16 MiB cotejada con QMP, el estado
`03`, teclado y raton USB simultaneos y el rechazo SBEF W+X. En HOST,
la rutina compilada con servicios UEFI simulados verifica la lectura
GA106, los rechazos y la liberacion de buffers. El lector ocupa 3880 B
de la pagina EFI de 4096 B.

El arranque en METAL del 20-11-2026 obtuvo `GPU_MMIO_STATUS=00000008`,
`GPU_BAR0_LEN=01000000` (16 MiB informados por UEFI) y
`GPU_PMC_BOOT0=B76000A1` (GA106 A1). Coincide con la lectura de BMO-X
para esta tarjeta. El registro se genero antes de ExitBootServices y
acredita la lectura MMIO. El escritorio sigue usando CPU + GOP.
[Informe MMIO de METAL](../Reports/nvidia-pci-metal-20261120-mmio.json).
[Identidad registrada por BMO-X](https://github.com/AndreeSalazar/BMO-X-x86-64/blob/6076bdefefc67877419ca53633c6e40cb45fc92d/platform/drivers/gpu/ga10x/ANATOMIA.md#L28).

El perfil `--nvidia-gsp-sample` agrega una captura previa al inicio
en `A:\BMO-X2\GPU\GPULOG.TXT`. La linea `GSP1` contiene, en orden, el
control RISC-V del GSP (`111388`), el buzon 0 del GSP (`110040`) y el
buzon 0 de SEC2 (`840040`). Son desplazamientos hexadecimales de BAR0.
La sonda exige la identidad GA106, los tres registros dentro de BAR0
y PCI Command estable con BME apagado. Publica las tres palabras juntas
o conserva los guiones. Los patrones de acceso denegado son valores
crudos del dispositivo y se conservan para diagnostico.

La lectura ocurre antes de ExitBootServices. Registra el estado heredado
de los motores, sin enviarles una orden de arranque. El ensayo HOST
ejecuta la sonda con un protocolo EFI simulado. Los tres casos QEMU
verifican que su VGA omite la lectura y que el arranque sigue su curso.
El candidato `run-rmlui-media-480776a07a14` reemplazo solo
`A:\EFI\BMO-X2\NVIDIA.EFI` y dejo un respaldo verificado. Elegir la
entrada **BMO-X2 (con NVIDIA)** para producir la primera captura de METAL.
[Prueba y despliegue](../Reports/nvidia-gsp-boot-sample-20261120.json).
[Registros GSP](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/inc/swref/published/ampere/ga102/dev_gsp.h).
[Control RISC-V](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/inc/swref/published/ampere/ga102/dev_riscv_pri.h).
[Base MMIO de SEC2](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/inc/swref/published/ampere/ga102/dev_sec_pri.h).

La primera captura METAL de este perfil obtuvo
`GSP1=00000010,00000000,00000000`. El control RISC-V marca HALTED y
ACTIVE_STAT a cero. Los buzones reportan cero antes de enviar una
orden. PCI Command sigue en `0003` y AMD-Vi tiene la traduccion apagada.
[Registro UEFI de la RTX](../Reports/nvidia-pci-metal-20261120-gsp-sample.bootlog.txt).

ULTRA-LinuX activo la traduccion AMD-Vi antes de cargar `nvidia-open`.
La prueba del 20 de noviembre registro firmware `615.78.08` en la
RTX `29:00.0`, `nvidia-drm` inicializado y HDMI-A-1 a 1920x1080 en
la sesion Hyprland en modo NVIDIA. La preparacion DMA del driver precede
al traspaso de pantalla. El lector de BMO-X2 recoge la geometria desde
UEFI para preparar ese paso en su propio controlador.
[Compilacion de nvidia-open para el kernel de ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/27fafba1ea733b67ced86f375427c189121b7b97/scripts/build-baseline.sh#L160-L186).

En el perfil Full HD la fila `WPR` de `GPULOG.TXT` contiene ocho
palabras de 32 bits, en orden: permiso y progreso GFW, MiB de VRAM
utiles, base VGA, permiso y limites inferior y superior del bloqueo
MMU, y limite superior de WPR2. La captura se publica despues de
releer PCI Command. Una lectura incompleta conserva la fila con
guiones. El analizador distingue una region MMU ausente de una
region valida y distingue WPR2 activa de una captura invalida.
Para codificar WPR, `locked_start: null` indica que VBIOS no marco una
region. El valor `0` representa un bloqueo valido desde la pagina cero.

```powershell
python -B -m tools.host.gpu.NVIDIA.gsp_wpr A:/BMO-X2/GPU/GPULOG.TXT --from-bootlog
```

Esta lectura permite determinar si el estado previo del firmware
acepta un arranque en frio. La traduccion DMA nativa, el traspaso
de almacenamiento y la respuesta del GSP se validan por separado.
La captura de la RTX 3060 GA106 confirma 12 GiB de VRAM, VBIOS
inicializada y WPR2 desactivada. Los limites de bloqueo MMU se
conservan como diagnostico. En 615.78.08 la regla que los usa para
recortar la ventana WPR se asigna a GA100. Para GA106 se toma la
ventana de 256 MiB preinicializada al final de VRAM.
[Evidencia de ULTRA-LinuX y de la sonda WPR](../Reports/nvidia-wpr-ultra-linux-20261121.json).
[Captura real y preparacion WPR de GA106](../Reports/nvidia-wpr-fwsec-metal-20261121.json).
[Seleccion de implementacion MMU por GPU](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/generated/g_mem_mgr_nvoc.c#L1303-L1315).
[Limites VGA segun NVIDIA](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/disp/arch/v04/kern_disp_0400.c).
[Registros de bloqueo MMU](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/common/inc/swref/published/ampere/ga100/dev_fb.h).

El perfil `--nvidia-gsp-stage` sin preparacion agrega el original `GSP.BIN` de
`615.78.08` en `A:\BMO-X2\GPU\`. El HOST coteja la huella fijada y
valida las secciones ELF. UEFI lee exactamente 27 043 992 B, coteja
CRC32 y reserva 6603 paginas `EfiLoaderData`. Entrega base, longitud
y estado al supervisor. El coste de la reserva es 26 MiB redondeados.
El paso de FAT32 a RAM precede a la carga del firmware en la GPU.

El mismo perfil produce `GSPLOAD=00000005` tras una lectura correcta,
`00000001` si falta el archivo, `00000002` si falla la reserva,
`00000003` si falla la lectura, el tamano o el cierre, y `00000004`
si falla la integridad. Los fallos dejan continuar el escritorio.
En QEMU se comparan los bytes residentes despues de EBS con la
huella de origen, la reserva del mapa EFI y las paginas de supervisor.
[Evidencia de archivo y RAM](../Reports/nvidia-gsp-stage-20261120.json).
[Calculo CRC32 en UEFI](https://uefi.org/specs/UEFI/2.10/07_Services_Boot_Services.html#efi-boot-services-calculatecrc32).

El siguiente arranque fisico obtuvo `GSPLOAD=00000005` y
`GSP1=00000010,00000000,00000000`. El contenedor llego a RAM y
el GSP seguia detenido. PCI Command y AMD-Vi conservaban sus permisos
anteriores al traspaso.
[Lectura fisica del contenedor](../Reports/nvidia-pci-metal-20261120-gsp-stage.bootlog.txt).

El banco AMD-Vi prepara la imagen firmada y la firma GA10x en paginas
de 4 KiB alineadas. La imagen empieza a 64 B dentro del ELF y la firma comienza
en otro desplazamiento no alineado. El directorio Radix3 usa las IOVA
de las paginas de imagen resultantes. Las 6606 paginas de imagen,
firma y directorio tienen permiso de lectura del dispositivo y solo
una pagina de respuesta admite escritura. El dominio de prueba usa
la funcion grafica `29:00.0`; la funcion de audio `29:00.1` tiene una
raiz vacia. El hueco entre el firmware y la respuesta queda sin mapa.

QEMU, con dos funciones EDU emuladas, transfiere todas esas paginas
y coteja su SHA-256. Tambien comprueba bloqueos de firmware, hueco,
audio y revocacion. El banco lo programa mediante qtest, sin ejecutar
Ring 0 del invitado. El cargador de la RTX requiere asignar este
dominio desde el kernel fisico, con los demas solicitantes del equipo
bajo control, y ejecutar la secuencia firmada del GSP.
[Prueba DMA del paquete completo](../Reports/nvidia-gsp-dma-qemu-20261120.json).
[Comandos y formatos AMD-Vi](https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/specifications/48882_IOMMU.pdf).

#### Perfil NVIDIA opcional

El codigo del perfil vive en `kernel/drivers/GPU/NVIDIA/`. Sus
herramientas y el manifiesto de firmware viven en
`tools/host/gpu/NVIDIA/`. El escritorio base se construye con
`--usb both`; las opciones NVIDIA agregan sus includes y archivos
al candidato dedicado. Para arrancar el perfil base se usa su
`DESKTOP.EFI` independiente. Al preparar el perfil sin NVIDIA se
omiten las dos carpetas del modulo.
El perfil base puede conservar las sondas de plataforma con
`--usb both --amdvi-probe --amdvi-post`. Sus registros aparecen en
`BMO-X2/DESKTOP/BOOTLOG.TXT`.

Con `--nvidia-gsp-prepare`, la entrada del loader llama a una rutina
privada de Ring 0 tras ExitBootServices. La rutina vuelve a comprobar
la reserva EfiLoaderData y coloca `.fwimage` y la firma GA10x en limites
de pagina de la misma reserva. Ring 0 construye las 15 paginas Radix3
y 14 paginas AMD-Vi para exponer imagen, firma y directorio como solo
lectura. Luego prepara RMARGS, GspMem y LIBOS en una hoja AMD-Vi
compartida. Las tablas AMD-Vi quedan fuera de las IOVA de la GPU.
El supervisor publica estado 5 y el pie del escritorio indica
**NVIDIA / LIBOS y colas GSP listos / DMA pendiente**. Las tablas quedan en RAM hasta la adjudicacion
del dominio. El indice 6 del diagnostico AMD-Vi entrega los estados de
archivo y preparacion a Ring 3.

ULTRA-LinuX arranco esta misma RTX 3060 con `nvidia-open` y GSP
`615.78.08`, y preparo el control de pantalla con `nvidia-modeset` y
`nvidia-drm`. BMO-X2 conserva esa separacion de hitos. Preparar las
tablas deja por verificar la adjudicacion de DMA con USB y discos
activos, la respuesta del GSP y el primer trabajo grafico.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --dma-census --storage-state --full-hd --nvidia-gsp-sample --nvidia-gsp-stage build/gpu/NVIDIA/ga10x-615.78.08 --nvidia-gsp-prepare
python -B -m tools.host.gpu.NVIDIA.qemu_gsp_dma build/gpu/NVIDIA/ga10x-615.78.08
```

[Pruebas de independencia y preparacion NVIDIA](../Reports/nvidia-gsp-prepare-qemu-20261120.json).
[Arbol preparado por Ring 0 y verificado en QEMU](../Reports/nvidia-gsp-detached-dma-qemu-20261120.json).
[Colas GSP y dominio DMA en el bus PCIe 29](../Reports/nvidia-gsp-queues-routed-qemu-20261121.json).

Despues del estado `08` quedan tres pruebas:

1. Preparar la version compatible de GSP y su procedencia. Reservar y
   aislar los buffers de arranque antes de conceder bus mastering.
   Acreditar el inicio mediante la respuesta del GSP y registrar el
   punto de fallo si se agota el plazo de espera.
2. Ejecutar una operacion acotada sobre un buffer dedicado y comprobar
   su contenido. Esto acredita que la GPU puede producir un resultado.
3. Verificar el control de salida NVIDIA: configurar modo y conector,
   mostrar un cuadro de prueba y comprobar su reemplazo sincronizado.
   Luego DIRECTOR/RmlUi puede presentar por ese backend.

#### Preparacion HOST del arranque GSP

HOST comprobo los binarios locales `booter_load`, `booter_unload`,
`bootloader` y `gsp` de cada release por longitud y SHA-256. El conjunto
`570.144` permite comparar la futura secuencia nativa con VERRANO. El
conjunto `615.78.08` corresponde a la version observada en ULTRA-LinuX.
Es la release fijada como objetivo de BMO-X2. La opcion `native`
del verificador selecciona ese conjunto completo.
El verificador usa huellas de referencia del conjunto local, y rechaza
archivos alterados y releases cruzadas. La autenticacion de firmware
en hardware y el intercambio con el GSP quedan para el ensayo de
arranque. [Verificacion HOST](../tools/host/gpu/NVIDIA/firmware.py).
[Procedencia de 570.144 en linux-firmware](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/%2B/refs/tags/20250917/WHENCE).
[GSP 615.78.08 de NVIDIA](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/gsp.html).

El HOST acepta `--layout` para inspeccionar el contenedor GSP de la
release nativa despues de comprobar las cuatro huellas. Selecciona
`.fwimage`, `.fwversion` y `.fwsignature_ga10x` del ELF64 RISC-V,
y comprueba longitud, limites, version y solapamiento. La imagen
firmada ocupa 26 992 640 B, equivalentes a 6590 paginas de 4 KiB.
La firma GA10x ocupa 4096 B. Este inventario describe las piezas
del archivo. Las colas RPC, metadatos, lanzamiento y respuesta GSP
se comprueban en fases posteriores.
[Distribucion del firmware verificada en HOST](../Reports/nvidia-gsp-layout-20261120.json).

Las cuatro piezas originales de `615.78.08` se copiaron al directorio
local `build/gpu/NVIDIA/ga10x-615.78.08` para el cargador NVIDIA separado.
Las longitudes, las huellas y las secciones coinciden con el original.
El manifiesto de esa copia registra la comprobacion HOST.

El codificador `tools/host/gpu/NVIDIA/radix3.py` arma un directorio para
`.fwimage` usando las IOVA de reserva que recibe. Cada entrada
es una direccion LE64 visible al dispositivo. Las listas de imagen
y del directorio se comprueban por tamano, alineacion y unicidad.
En HOST se verificaron 15 paginas de directorio para las 6590
paginas de la imagen 615.78.08. Un recorrido independiente
reconstruyo su huella con IOVA no contiguas de ensayo. En METAL
las IOVA deben venir de un dominio DMA activo y autorizado.
[Evidencia Radix3](../Reports/nvidia-gsp-radix3-host-20261120.json).
[Directorio GSP en NVIDIA](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c#L7198-L7343).

La sonda x86-64 de `kernel/drivers/GPU/NVIDIA/gsp_radix3.inc` recibe
dos rangos IOVA contiguos y un buffer reservado
por el supervisor. Valida alineacion, capacidad, limite de direccion y
solapamiento antes de escribir. La prueba HOST coteja byte por byte el
directorio de 15 paginas del ensayo DMA y cinco geometrias de borde.
El perfil NVIDIA la llama tras ExitBootServices para preparar el arbol
DMA en RAM. En METAL queda pendiente adjudicar las IOVA a la RTX.
[Resultados del banco](../Reports/nvidia-triangle-host-20261120.json).

El codificador HOST de `615.78.08` sirve de referencia para la pagina
RMARGS y las 129 paginas GspMem que ahora inicializa Ring 0. QEMU
coteja todos sus bytes y verifica la hoja DMA. RMARGS y la tabla de
paginas son de solo lectura, y ambas colas admiten escritura. La cola
CPU a GSP recibe la cabecera MSGQ 2.0 y la de retorno queda a cero
para que el GSP la inicialice.
[Codificador HOST](../tools/host/gpu/NVIDIA/gsp_args.py).
[Estructura RMARGS](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/inc/kernel/gpu/gsp/gsp_init_args.h).
[Formato MSGQ 2.0](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/inc/libraries/msgq/msgq_priv.h).

El perfil preparado anade 99 paginas para LIBOS 3. Una pagina de
solo lectura contiene las ocho descripciones de log y RMARGS. Las
98 paginas de log admiten DMA de lectura y escritura. LIBOS
reutiliza la hoja DMA de las colas.
El estado 5 indica que Ring 0 publico la IOVA de LIBOS. El primer
resultado de la RTX requiere adjudicar el dominio real, preparar
WPR y recibir la confirmacion del firmware antes del trabajo 3D.
[Seleccion de logs y arranque de NVIDIA 615.78.08](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c).
[Formato de argumentos LIBOS](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/common/uproc/os/common/include/libos_init_args.h).
[Registro METAL, referencia Vulkan y ensayo LIBOS en QEMU](../Reports/nvidia-gsp-libos-20261121.json).

Con `--nvidia-gsp-prepare`, `GSP.BIN` contiene el ELF original y un
trailer de 33 paginas con el monitor RISC-V y los binarios SEC2 de
carga y descarga. El CRC32 cubre ambos. Ring 0 conserva los bytes
firmados al reordenar la reserva y agrega las 33 paginas de solo
lectura a la hoja DMA existente. La reserva suma 6884 paginas con
la pagina WPR. Esta se publica en `0x0a106000` dentro del arbol
DMA separado cuando la muestra GA106 permite el arranque en frio.
QEMU verifico el trailer y el rechazo del archivo con un byte
alterado en el trailer. EDU leyo una pagina del monitor y recibio un
fallo al escribir otra pagina del monitor sin lectura previa.

`tools/host/gpu/NVIDIA/gsp_wpr.py` emite los 256 bytes de WPR V1 a
partir de los limites efectivos de VRAM y las IOVA del firmware.
Comprueba la reserva de la VBIOS, la ventana permitida y los
solapamientos. Con la captura real de GA106, la rutina de Ring 0
produce el mismo bloque de 256 bytes que la referencia C y el HOST.
El intervalo WPR calculado es `0x2f6300000..0x2fff00000`. FRTS
ocupa el ultimo MiB, desde `0x2ffe00000`. Ring 3 muestra `WPR preparada`
cuando existe el bloque. En QEMU, la VGA virtual conserva la pagina
vacia y sin IOVA publicada.

El HOST prepara la orden FRTS con el FWSEC firmado de la VBIOS medida.
Con `--nvidia-fwsec-vbios <VBIOS.ROM>`, el empaquetador valida la huella
de la VBIOS MSI e incluye el codigo y las tres firmas originales en el
archivo verificado. Durante el arranque, la sonda confirma el subsistema
`1462:397D`, toma el fusible mediante EFI PCI I/O y relee PCI Command.
Con WPR disponible, Ring 0 fija base y longitud FRTS, incorpora la firma
original que corresponde al fusible y publica 15 paginas DMA de solo
lectura desde `0x0a107000` en el arbol separado. El escritorio informa
`FWSEC listo para cargar`. La reserva total sube a 6899 paginas.
Ante otra GPU, un fusible invalido o WPR activa, Ring 0 borra esa region
y deja la IOVA sin publicar.

```powershell
python -B -m tools.host.gpu.NVIDIA.gsp_wpr limites-y-layout.json wpr.bin
python -B -m tools.host.gpu.NVIDIA.gsp_fwsec vbios.rom wpr.bin fwsec
```

La [sonda de arranque de Falcon](../kernel/drivers/GPU/NVIDIA/fwsec_launch.S)
emite 226 transferencias de 256 B a IMEM y 8 a DMEM para el FWSEC firmado
de esta GA106. Configura BROM, emite STARTCPU y exige HALT, buzon y
SCRATCH14 sin error, y WPR2 `02FFE000/02FFEE00`. El plazo total es de
dos segundos a partir del TSC calibrado. El banco HOST enlaza esa misma
rutina y simula la respuesta de los registros de Falcon.

La preparacion de Falcon selecciona el nucleo, mantiene el reset al menos
10 us y espera un maximo de 20 ms por la limpieza de memoria y el estado
listo. El llamador conserva el bus mastering de la GPU apagado durante
esta preparacion. El banco HOST cubre el estado frio, los rechazos antes
de escribir y los plazos agotados con registros simulados.

Estas rutinas quedan fuera del arranque desplegado hasta que el llamador
adquiera el dispositivo y adjudique el DMA fisico con todos los
solicitantes bajo control. Un fallo requiere cerrar el bus mastering
y detener la GPU antes de recuperar las paginas. El resultado de FWSEC
habilita la siguiente etapa de SEC2. GSP y el resultado escrito por la
RTX se verifican por separado.
[Banco HOST de FWSEC](../tools/host/gpu/NVIDIA/test_fwsec_launch.py).
[Reset del motor Falcon](https://codebrowser.dev/linux/linux/drivers/gpu/drm/nouveau/nvkm/falcon/gp102.c.html#67).
[Seleccion y espera de Falcon en Ampere](https://codebrowser.dev/linux/linux/drivers/gpu/drm/nouveau/nvkm/falcon/ga102.c.html#70).
[Verificacion del arranque firmado y WPR V1](../Reports/nvidia-gsp-boot-chain-20261121.json).
[Preparacion FWSEC-FRTS con la VBIOS GA106](../Reports/nvidia-wpr-fwsec-metal-20261121.json).
[Seleccion de firma FWSEC para Ampere en Nouveau](https://codebrowser.dev/linux/linux/drivers/gpu/drm/nouveau/nvkm/subdev/gsp/ga102.c.html#95).
[Geometria WPR V1 en NVIDIA 615.78.08](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c).

La tabla ACPI IVRS del equipo tiene 208 B y describe tanto
`0000:29:00.0` (RTX) como `0000:29:00.1` (audio) bajo la unidad
AMD-Vi `0000:00:00.2`, con base MMIO `0xFD500000`. El inventario
usa la descripcion extendida IVHD `0x11`. ULTRA-LinuX tambien registra
ambas funciones en el grupo IOMMU 16. El grupo de Linux es una
observacion de ese sistema. La asignacion y revocacion del dominio en
BMO-X2 requieren una prueba propia.
[Lector IVRS HOST](../tools/host/gpu/ivrs.py).
[Informe del equipo](../Reports/nvidia-gsp-host-20261120.json).
[Registro AMD-Vi de ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX/blob/7c275c1a716a80226ff83e340258fb1cd6bb08c3/evidencias/pc-real/nvidia-2026-10-19/dmesg-pc.txt#L584-L624).

```powershell
python -B tools/host/gpu/ivrs.py 0000:29:00.0 0000:29:00.1
python -B tools/host/gpu/NVIDIA/firmware.py native ..\BMO-externo\firmware\nvidia\ga102\gsp
python -B tools/host/gpu/NVIDIA/firmware.py 570.144 ..\BMO-externo\firmware\nvidia\ga102\gsp
python -B tools/host/gpu/qemu_dma.py
```

QEMU `q35` con `amd-iommu,dma-remap=on` y EDU ya reproduce una
transferencia de 14 bytes mediante una pagina autorizada, rechazo fuera
del rango, e invalidacion confirmada seguida de un segundo rechazo. qtest
programa los dispositivos emulados y lee RAM para comprobar que las
peticiones rechazadas dejan intactos los marcadores. Esta version de QEMU
registra los fallos de pagina con el solicitante EDU y direccion cero.
El resultado se verifica tambien en RAM y el informe guarda las
direcciones de eventos tal como las entrega QEMU.
[Prueba AMD-Vi en QEMU](../Reports/nvidia-amdvi-qemu-20261120.json).
[Dispositivo EDU](https://www.qemu.org/docs/master/specs/edu.html).

La sonda de BMO-X2 `run-amdvi-edu-d34bb76f3647` repitio la concesion y
revocacion desde CPL0 despues de `ExitBootServices`. Arranco desde FAT32
con el puente heredado y programo AMD-Vi para EDU. QEMU comprobo la
transferencia de ocho bytes a una pagina de 4 KiB autorizada, el bloqueo
fuera de rango y el bloqueo despues de revocar. El caso sin IOMMU se
detuvo en la deteccion, y el caso que omite la invalidacion detecto la
traduccion antigua y cerro bus mastering. Es una sonda ASM exclusiva de
QEMU TCG. [Prueba desde BMO-X2](../Reports/amdvi-edu-native-qemu-20261120.json).

#### Punto de prueba antes de reiniciar

El perfil `--nvidia-probe --amdvi-probe` agrega una sonda UEFI de
solo lectura. Valida las sumas de RSDP, XSDT e IVRS, localiza una unidad
IVHD del segmento PCI 0 y coteja su base con la capacidad PCI AMD.
La sonda restaura el selector PCI y deja el subsistema DMA en manos del
firmware durante la captura.
[Tablas ACPI](https://uefi.org/specs/ACPI/6.5_A/05_ACPI_Software_Programming_Model.html).
[Registros AMD-Vi](https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/specifications/48882_IOMMU.pdf).

`run-rmlui-media-38ddb012ee7e` paso los dos arranques en QEMU q35.
Con AMD-Vi, el BDF coincide con QMP y la base es `FED80000` con
decodificacion desactivada. El otro arranque registra la ausencia de
IVRS y rechaza el SBEF W+X. Con la sonda, el lector ocupa 3956 B
dentro de su pagina y el EFI ocupa 28 KiB. El paquete CASM, el
escritorio SBEF y la etapa xHCI conservan sus bytes.
[Evidencia QEMU](../Reports/amdvi-firmware-uefi-qemu-20261120.json).

La linea `AMDVI=` en `A:\BMO-X2\GPU\GPULOG.TXT` presenta cinco
palabras hexadecimales en orden: estado, longitud IVRS validada, BDF
de la unidad, mitad baja de la base PCI con bit de habilitacion y
mitad alta. Los guiones representan campos sin lectura.

| Estado | Captura pre-EBS |
|---|---|
| `00` | IVRS ausente |
| `01` | Raiz ACPI invalida |
| `02` | IVRS invalida |
| `03` | Unidad unica del segmento 0 no identificada |
| `04` | Capacidad PCI AMD-Vi ausente o invalida |
| `05` | La base PCI difiere de IVRS |
| `06` | Bases iguales, decodificacion MMIO desactivada |
| `07` | Bases iguales, decodificacion MMIO activa |

El arranque en METAL de `run-rmlui-media-38ddb012ee7e` obtuvo
`AMDVI=00000007 000000D0 00000002 FD500001 00000000`.
Los 208 B de IVRS, la unidad `0000:00:00.2` y la base
`0xFD500000` coinciden con el inventario HOST. El bit bajo de
`FD500001` indica que la decodificacion PCI de la ventana MMIO
estaba habilitada. La RTX `0000:29:00.0` sigue reportando
`PCI Command=0003`, con bus mastering apagado en la captura.
[Informe AMD-Vi de METAL](../Reports/nvidia-pci-metal-20261120-amdvi.json).

El candidato con captura de registros agrega `AMDVI_MMIO=` al mismo
archivo. Sus campos son estado, control, base y tamano de la tabla de
dispositivos, base de la cola de comandos, base de la cola de eventos
y estado de AMD-Vi. El estado de captura ocupa ocho digitos. Cada
registro ocupa dieciseis digitos, con bits de tamano y control tal como
los entrega el hardware.

| Estado de captura | Significado |
|---|---|
| `00` | Lectura omitida tras el inventario |
| `01` | Ventana fuera del rango admitido |
| `02` | Protocolo CPU I/O 2 no disponible |
| `03` | Protocolo rechazo la lectura o devolvio todo unos |
| `04` | Cinco registros leidos |

Con captura `04`, el bit 0 del registro de control indica si la
traduccion estaba habilitada en ese instante. La sonda lee a traves
de CPU I/O 2 antes de ExitBootServices. En QEMU TCG, el dispositivo
AMD-Vi emulado mapea su ventana fija aunque el bit PCI de decode este
apagado. El banco EDU mide por separado el estado posterior al
traspaso usando la ventana conocida del emulador.
[Protocolo CPU I/O 2](https://uefi.org/specs/PI/1.8A/V5_CPU_I_O_Protocol.html).

`run-rmlui-media-a3d1dd3a0584` cotejo los cinco registros del
FAT32 con QMP. El caso sin AMD-Vi conservo los campos sin lectura
y rechazo el SBEF W+X. En un invitado separado,
`run-amdvi-edu-1c911676f597` comprobo AMD-Vi inactivo al entrar
en CPL0 y el readback con traduccion activa antes del DMA de EDU.
Los casos sin IOMMU y sin invalidacion conservaron sus rechazos.
El lector EFI ocupa 4070 B de su pagina de 4096 B.
[Evidencia de ambas pruebas QEMU](../Reports/amdvi-registers-qemu-20261120.json).

En METAL, el mismo candidato obtuvo captura `04` y control
`0000220000000400`. `IommuEn`, `CmdBufEn` y `EventLogEn` estaban
a cero antes del traspaso. El registro de tabla de dispositivos y
el de estado tambien eran cero. El firmware habia programado bases
de comandos (`0x1023F8000`) y eventos (`0x1023FA000`). La captura
registra los valores de esos registros. La propiedad de las paginas
apuntadas queda por comprobar.
[Captura de registros en METAL](../Reports/nvidia-pci-metal-20261120-amdvi-registers.json).

El siguiente arranque en METAL, con `run-rmlui-media-61ebf6ff6e23`,
cotejo `GPULOG.TXT` con la foto del informe Ring 0. Los cinco
registros coincidieron dentro de ese mismo arranque. El control siguio
en `0000220000000400`, tabla y estado en cero, y las colas siguieron
desactivadas con bases `0x1023F7000` y `0x1023F9000`. Esas bases
difieren de las del arranque anterior.
[Captura posterior al traspaso en METAL](../Reports/nvidia-pci-metal-20261120-amdvi-post-ebs.json).

Siguientes pruebas y criterio de avance:

1. Capturar los solicitantes PCI con bus mastering habilitado despues
   de iniciar xHCI. Cada solicitante requiere mapeos validados o una
   parada confirmada antes de activar la traduccion. El registro fisico
   pre-EBS muestra dos xHCI con bus mastering habilitado.
2. Probar primero la tabla y las colas propias en METAL con la RTX y
   su funcion de audio sin bus mastering. Verificar que USB sigue
   operativo y, cuando el perfil disponga de acceso nativo al disco,
   verificar una lectura con traduccion activa. Despues acreditar
   acceso DMA concedido, rechazo fuera de rango y revocacion confirmada
   en el dominio de la RTX. Retener los marcos si falla la invalidacion.
3. Arrancar GSP `615.78.08` con los buffers autorizados y verificar
   una respuesta valida. Luego ejecutar una operacion sobre un buffer
   dedicado, comprobar su salida y demostrar dibujo 3D fuera de
   pantalla antes de entregar el conector al backend NVIDIA.
[Contrato DMA](../kernel/drivers/bus/DMA.md).

El ensayo `run-rmlui-media-a5d049f8da32` registro 8 B transferidos
a la pagina de EDU, rechazo fuera de rango y rechazo tras revocar.
El escritorio recibio dos informes de teclado y uno de raton en
cada etapa. HOST configuro AMD-Vi mediante qtest y suspendio
temporalmente bus mastering de otras funciones PCI emuladas.
El ensayo conserva el candidato METAL instalado y esta bloqueado
para despliegue.
[Evidencia de coexistencia](../Reports/amdvi-xhci-coexist-qemu-20261120.json).

En `run-rmlui-media-aa8163cdd899`, Ring 0 activo los dominios,
confirmo la invalidacion y cerro AMD-Vi. Se verificaron los dos
dispositivos USB durante la concesion y tras revocar la pagina de
EDU. La primera solicitud se rechazo con otros bus masters activos.
En este ensayo el HOST suspendio los otros solicitantes emulados
y el medio queda confinado a QEMU.
[Evidencia del kernel invitado](../Reports/amdvi-xhci-guest-qemu-20261120.json).

El candidato `--dma-census` registra una vez el segmento PCI 0 desde
Ring 0, despues de iniciar USB. Guarda hasta 64 registros con BDF,
identificadores, clase y comando PCI. Guarda tambien el total aunque
supere el espacio disponible y el BDF del xHCI que atiende el escritorio.
El bit BME indica permiso para iniciar DMA. Los puentes tambien pueden
tenerlo habilitado. La captura no mide trafico, rangos DMA ni reservas
de firmware. Solo se modifica el selector de lectura PCI y se restaura
al terminar. La captura usa el contexto supervisor ya reservado.

Desde la entrada **BMO-X2 (con NVIDIA)**, **F2** abre y cierra
el inventario en Ring 3. F3 pasa a la pagina siguiente cuando hay
mas de 16 filas. Para la prueba fisica, mover el raton, abrir el
panel con F2 y guardar una foto de las filas. `GPULOG.TXT`
recoge la etapa anterior a `ExitBootServices`. El inventario posterior
aparece en pantalla y en la serie. Se conserva la presentacion CPU + GOP.
El ensayo `run-rmlui-media-4714e8306aab` cotejo nueve funciones
con qtest, entre ellas el xHCI detras de un puente PCIe. Sin AMD-Vi
cotejo ocho funciones. Paso tambien el rechazo SBEF W+X.
La sonda suma 264 B de codigo y el paquete queda en 4052 B.
El 20-11-2026 se verificaron el despliegue de los tres archivos del
perfil NVIDIA en `A:` y los respaldos de sus versiones anteriores.
[Prueba del inventario PCI en QEMU](../Reports/dma-pci-census-qemu-20261120.json).

La captura F2 del equipo AMD mostro quince funciones con BME,
incluidos el xHCI activo `2b:00.3`, un segundo xHCI `03:00.0`,
AHCI `03:00.1` y NVMe `01:00.0`. La lectura HOST de IVRS ubico
esas quince funciones y las dos funciones NVIDIA en el mismo
IVHD `11`, unidad `00:00.2` y ventana `FD500000`. Para esas
direcciones, el analizador no encontro un alias declarado.
En el arranque fotografiado, la RTX seguia con comando PCI
`0003`, con BME apagado.
[Inventario METAL y cotejo IVRS en HOST](../Reports/dma-pci-census-metal-20261120.json).

El candidato `--storage-state` agrega una pagina de almacenamiento
al inventario. UEFI registra hasta dos controladores AHCI/NVMe del
segmento 0 con el recurso informado por EFI PCI I/O. Ring 0 vuelve
a cotejar identidad, comando y BAR despues de `ExitBootServices`,
antes de iniciar xHCI. Solo abre una ventana temporal UC, de
supervisor, lectura y NX, si el recurso coincide y sus paginas
quedan fuera de RAM en el mapa final. La ventana se revoca al
terminar. Un recuento incompleto o un estado MMIO sin confirmar
requiere otra comprobacion antes de transferir el controlador.

Desde **BMO-X2 (con NVIDIA)**, pulsar **F2** y **F3** hasta ver
**Almacenamiento al salir de UEFI**. Fotografiar ambas filas.
Para SATA, `Motores` es una mascara de puertos con ST, FRE, CR
o FR y `Comandos pendientes` recoge los que tienen PxCI o PxSACT.
Para NVMe se muestran CC, CSTS, EN, RDY y CFS. Un motor habilitado
puede estar ocioso entre comandos. Capturar estos registros
determina que transicion necesita cada controlador antes de
activar AMD-Vi. El candidato no inicia comandos ni cambia registros
de AHCI/NVMe o la traduccion DMA. `GPULOG.TXT` sigue mostrando los
datos pre-EBS. La captura posterior se lee en pantalla y en serie.
El candidato `run-rmlui-media-028165bacf7a` paso los tres casos
de QEMU y se verifico en FAT32 `A:`. Se guardaron las versiones
previas de NVIDIA.EFI y DESKTOP.SBF. INICIO.X86 coincide byte a
byte con el candidato anterior.
[Prueba AHCI/NVMe y panel F3 en QEMU](../Reports/storage-state-qemu-20261120.json).
[Especificacion AHCI](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/serial-ata-ahci-spec-rev1-3-1.pdf).
[Especificacion NVMe](https://nvmexpress.org/specification/nvm-express-base-specification/).

La captura METAL de ese candidato muestra motores SATA activos
en los puertos 4 y 5 (`Motores 00000030`), con PxCI/PxSACT a
cero en ese instante. El NVMe `01:00.0` sigue habilitado y listo
(`EN=1`, `RDY=1`, `CFS=0`). Los dos conservan PCI Command
`0006`. El traspaso nativo requiere detener los motores AHCI
en orden y confirmar su parada, y completar el cierre controlado
de NVMe antes de retirar sus colas y el permiso DMA. La ausencia
de comandos SATA pendientes por si sola no confirma la parada.
[Captura y registro del equipo fisico](../Reports/storage-state-metal-20261120.json).

El mismo registro METAL muestra un modo GOP de 1920x1080. El
perfil anterior presentaba una superficie centrada de 1280x800.
La primera version de `--full-hd` adapto RmlUi a 1280x720 y presento
en proporcion 3:2 sobre los 1920x1080 completos mediante CPU. El
escalador aplicaba la misma regla a cuadros completos, puntero y
franja de bloqueos. Para otros modos conservo el presentador base.
El candidato `run-rmlui-media-6202354d7e32` paso los tres casos de QEMU.
La prueba comparo los 2073600 pixeles de salida y verifico las regiones
del puntero y los bloqueos sin rasterizar otro cuadro. Se desplego en
el perfil NVIDIA de `A:` con hashes verificados y respaldo de NVIDIA.EFI
y DESKTOP.SBF. El indicador `CPU / GOP 1080p` identifica este modo.
[Presentacion de Full HD y retornos de modo en QEMU](../Reports/gop-full-hd-qemu-20261120.json).

El usuario confirmo en METAL que el perfil anterior llena la pantalla y
observo bordes y texto poco nitidos. El nuevo `--full-hd` compone en Ring 3
a 1920x1080. RmlUi aplica la densidad de 1.5 a las medidas y FreeType
genera los glifos a su tamano final. GOP copia una vez cada pixel de
la superficie. Mantiene cajas de 12x17 para el puntero y 120 filas para
los indicadores. Fuera del modo exacto usa el presentador base.
El framebuffer XRGB ocupa 8294400 B. El perfil reserva 18 MiB de RAM
para la UI, con 12 MiB de datos y 2 MiB de pila, manteniendo los limites
RX/R y el rango DMA de xHCI separado. El dibujo por CPU sigue siendo el
respaldo para el futuro presentador NVIDIA.
El candidato `run-rmlui-media-a01f0170ccfa` paso tres casos de QEMU.
El banco cotejo los 2073600 pixeles, el detalle del titulo, el puntero,
los bloqueos, los atajos y los paneles F2/F3. Se verificaron los tres
archivos en FAT32 y sus respaldos. El indicador visible es
`CPU / 1080p nativo`. El propietario confirmo la mejora de nitidez en
su monitor. El GPULOG de ese arranque registra 1920x1080 y la RTX
`10de:2504` en `29:00.0`, con comando PCI `0003`.
[Evidencia del raster nativo](../Reports/gop-native-full-hd-qemu-20261120.json).
[Densidad en RmlUi](https://mikke89.github.io/RmlUiDoc/pages/rcss/syntax.html#density-independent-pixel-dp).

#### Cierre AHCI y NVMe en QEMU

El perfil `--storage-quiesce` ejecuta la secuencia en Ring 0 antes de
iniciar xHCI. Se limita a TCG, a la ventana AMD-Vi del emulador con
traduccion apagada y a las dos identidades PCI del banco. AHCI exige
puertos sin comandos pendientes, desactiva ST y espera a CR, luego
desactiva FRE y espera a FR. NVMe solicita cierre normal con CC.SHN,
espera CSTS.SHST completo y confirma RDY en cero despues de quitar EN.
Tras la parada confirmada se limpia BME y se lee de vuelta PCI Command.
Los resultados se cotejan con los registros vivos mediante QEMU.

Un fallo conserva las reservas DMA heredadas y solo se retira BME tras
confirmar la parada. El perfil no emite medio instalable. Los casos
comprueban la salida con ambos controladores detenidos, informes HID
despues del cierre, rechazo SBEF W+X y ausencia de escrituras de la
sonda cuando falta AMD-Vi. El siguiente banco debe reiniciar las colas
propias y leer SATA y NVMe con AMD-Vi activo antes de probar la RTX.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --dma-census --storage-state --full-hd --storage-quiesce
```

[Evidencia del cierre en QEMU](../Reports/storage-quiesce-qemu-20261120.json).
[Especificacion AHCI](https://www.intel.com/content/dam/www/public/us/en/documents/technical-specifications/serial-ata-ahci-spec-rev1-3-1.pdf#page=112).
[Especificacion NVMe](https://nvmexpress.org/specification/nvm-express-base-specification/).

`--storage-quiesce-metal` usa la misma secuencia de parada para los
controladores capturados en la placa AMD. El perfil requiere `--full-hd`
y `--nvidia-fwsec-vbios`. Ring 0 exige la unidad AMD-Vi `00:00.2`
inactiva en `0xFD500000`, FWSEC listo para cargar, dos filas de
almacenamiento y la identidad PCI del controlador antes de escribir.
El SATA `1022:43B8` debe estar en `03:00.1`, sin comandos pendientes ni
propiedad del BIOS. El NVMe `2646:5017` debe estar en `01:00.0` con
CC.EN y CSTS.RDY activos. Los plazos se miden con TSC invariante,
calibrado con EFI Stall. El cierre normal de NVMe espera hasta cinco
segundos y la espera de RDY considera tambien CAP.TO.

F3 muestra la retirada de bus mastering tras confirmar la parada.
Una parada incompleta retiene las reservas DMA y se informa en F3.
El candidato `run-rmlui-media-362e700f8855` esta instalado en el menu
UEFI como **BMO-X2 (DMA SATA-NVMe)**. En el escritorio, F2 abre el
inventario PCI y F3 pasa al panel de almacenamiento. Capturar las dos
filas completas y `A:\BMO-X2\GPU\GPULOG.TXT`. QEMU verifica que
este binario omite la parada fisica en una placa distinta.
METAL confirmo la parada de NVMe `01:00.0` y SATA `03:00.1` el
22-11-2026. El panel F3 mostro PCI Command `0006 -> 0002` en ambos
controladores. El pie del escritorio mostro FWSEC preparado y la base
de la tabla AMD-Vi en cero. Antes de activar AMD-Vi aun se debe
transferir o detener el segundo xHCI y comprobar los solicitantes
restantes. Las lecturas de disco bajo traduccion siguen por verificar.
[Registro del arranque fisico](../Reports/amdvi-storage-handoff-metal-20261122.txt).

El ensayo optativo `--xhci-secondary-quiesce` agrega una comprobacion
al perfil de parada fisica. Solo considera el xHCI `1022:43BC` en
`03:00.0`, que queda fuera de la seleccion HID. Antes de retirar Bus
Master lee el estado del controlador y sus puertos mediante el alias
MMIO temporal: exige controlador detenido, sin reinicio ni errores,
puertos vacios y ninguna propiedad BIOS. Si alguna condicion falla,
conserva PCI Command. El inventario F2 posterior al inicio de HID
permite contrastar la fila `03:00.0` con el GPULOG previo a EBS.
El modulo opcional compilo en HOST, con 7,290 bytes de los 8,192
reservados. La prueba fisica y el dominio DMA de la RTX siguen pendientes.

El medio de prueba reutiliza el candidato SATA-NVMe
`run-rmlui-media-362e700f8855` y cambia unicamente el bloque xHCI del
EFI en el rango de archivo `0x4000..0x5fff`. El paquete SBEF, INICIO.X86,
GSP.BIN y el resto del EFI conservan sus bytes. Para comprobar el
resultado en METAL, abrir F2 y capturar todas sus paginas junto con
el GPULOG. El xHCI `2B:00.3` debe conservar teclado y raton mientras
se comprueba si `03:00.0` sigue en el inventario de Bus Master.
El candidato `run-rmlui-media-2826d337da7d` paso los tres casos QEMU,
incluida la entrada conjunta USB, y reemplazo el EFI de la entrada
**BMO-X2 (DMA SATA-NVMe)**. QEMU no tiene el controlador AMD `1022:43BC`;
la retirada fisica de su Bus Master se verifica en la placa.

En METAL, el GPULOG mostro `03:00.0` con PCI Command `0006` antes de
ExitBootServices. La foto posterior de F2 contiene 12 de 12 funciones:
`03:00.0` desaparece y `2B:00.3` sigue como xHCI activo con `0007`.
La captura acredita el cambio de Bus Master, no traduccion DMA.

`tools/host/gpu/NVIDIA/gsp_dma.py` genera una referencia HOST para la
tabla fisica completa de 65,536 entradas. Solo instala raices con
paginas accesibles para `29:00.0` (firmware de solo lectura y una
pagina de respuesta) y `2B:00.3` (14 paginas de xHCI con identidad
IOVA/fisica). El audio HDMI y los demas solicitantes apuntan a una
raiz vacia. La comprobacion HOST recorrio todas las DTE, un rango USB
que cruza 2 MiB y los permisos y huecos de ambos dominios. El formato
del laboratorio QEMU se conserva. Este modelo no se carga en METAL;
Ring 0 todavia debe construir y validar sus tablas con las reservas
reales y verificar el arranque del GSP.

La sonda ASM `physical_tables.S` implementa la construccion en memoria
privada para Ring 0. Recibe la raiz RTX ya validada por el llamador y
crea la raiz xHCI sin tocar registros AMD-Vi ni PCI. HOST ejecuto el
codigo nativo, inspecciono las 65,536 DTE y verifico las 14 paginas USB
cruzando dos hojas. Cinco entradas invalidas rechazadas conservaron
los buffers byte por byte. La sonda todavia no esta conectada al
arranque fisico.

`amdvi_prepare_from_efi_map` conecta ese constructor con el formato del
mapa EFI final. Antes de escribir valida por separado la DTE, el espacio
de trabajo, los buffers xHCI y la reserva completa de RTX como
`EfiLoaderData` bajo el mapa identidad de 256 MiB. La raiz RTX debe
caber dentro de su reserva y esa reserva no se puede solapar con las
otras tres. El llamador sigue siendo responsable de validar el arbol
RTX y la propiedad de los controladores. HOST ejecuto la entrada nativa
con memoria baja, un mapa valido y cinco mapas o reservas rechazados
sin modificar la tabla. Falta llamar esta entrada desde el arranque
fisico y comprobar la publicacion y revocacion de los dominios.

La variante optativa `--amdvi-physical-prepare` llama esa entrada desde
la preparacion NVIDIA pos-EBS. UEFI reserva 516 paginas adicionales al
final de la reserva del firmware: 512 para DTE y cuatro para las
raices y hojas xHCI. El constructor utiliza el mapa EFI final y la
reserva USB del mismo arranque. La variante requiere la entrega
experimental de SATA, NVMe y el xHCI secundario. QEMU inspecciona las
65,536 DTE antes de habilitar traduccion alguna. Ninguna de esas
tablas se publica todavia en AMD-Vi.
El candidato `run-rmlui-media-640292d69a5d` paso los tres casos QEMU.
La tabla se construyo en Ring 0 durante el arranque normal, y el
paquete de entrada con el saludo quedo en 4092 bytes.

La sonda `physical_mmio.S` separa la publicacion de bases de la
activacion. Exige el valor de Control observado en esta placa, estado
inactivo y punteros de cola en cero. Escribe y relee las bases de DTE,
comandos y eventos sin escribir Control. Conserva un recibo para devolver
las bases anteriores si la unidad sigue inactiva. Si no se puede
confirmar la restauracion, el llamador conserva las reservas. HOST
comprobo esta rutina con registros simulados, incluida la negativa
con punteros pendientes, estado activo o reservas solapadas.
[Especificacion AMD IOMMU, secciones 2.3.1, 2.4 y 2.5](https://docs.amd.com/api/khub/documents/GD6kOXjzWsek8QUbn_qMvg/content).

`--amdvi-physical-mmio-test` integra la transaccion en la captura
pos-EBS y agrega dos paginas vacias a la reserva NVIDIA para comandos
y eventos. Ring 0 solo la intenta en `FD500000`, con DTE preparadas y
FWSEC listo. Relee y restaura las bases antes de eliminar el alias
temporal, con la traduccion apagada durante todo el ensayo. QEMU usa
otra unidad y verifica que la transaccion se omite y las dos paginas
permanecen vacias. El escritorio lee el recibo de Ring 0. El campo
`Prueba AMD-Vi` muestra `101` si las bases se escribieron y restauraron,
`100` si fueron rechazadas antes de publicar, `102` si hubo una diferencia
y se confirmo la restauracion, `103` si la restauracion no se confirmo,
o `000` si el perfil no encontro las condiciones de la placa.

El candidato utiliza `EFI/BMO-X2/AMDVI-MMIO.EFI` y
`BMO-X2/GPU-MM`. Se instala como **BMO-X2 (AMD-Vi registros)** mediante
`deploy.ps1 -NvidiaProbe -ExperimentalUsb -AmdviMmio` y
`register-desktop.ps1 -NvidiaProbe -AmdviMmio`. El arranque conserva
el escritorio por CPU/GOP y deja AMD-Vi sin traduccion. La ejecucion
fisica de GSP sigue pendiente.

En METAL, `run-rmlui-media-116091803606` mostro `Prueba AMD-Vi 101`.
El GPULOG en `A:/BMO-X2/GPU-MM/GPULOG.TXT` identifica a la RTX
`29:00.0` con PCI Command `0003` y GSP detenido. Las fotos de ese
arranque muestran ambos discos en `0006 -> 0006` y xHCI `2B:00.3`.
El recibo en la mitad alta del estado hizo fallar la comparacion de
64 bits en el cierre de almacenamiento. El cierre vuelve a comprobar
el codigo en la mitad baja. Si la restauracion queda sin confirmar,
el codigo invalida la captura para operaciones de escritura.

En METAL, el candidato corregido `run-rmlui-media-f8c75c2c67a6`
mostro `0006 -> 0002` y parada confirmada tanto para NVMe `01:00.0`
como para SATA `03:00.1`. El GPULOG previo a EBS del mismo perfil
conserva la RTX identificada en `29:00.0` con Command `0003`. La
captura del panel confirma la entrega de almacenamiento. La activacion
de la traduccion se verifica aparte.

La [rutina de traduccion](../kernel/drivers/bus/amdvi/translation.S)
activa AMD-Vi con las tres bases ya cotejadas. Puede emitir una
invalidacion global seguida de la invalidacion del solicitante y una
orden COMPLETION_WAIT. El primer permiso de bus mastering queda a cargo
del llamador despues de esa respuesta. Durante el cierre, la rutina
repone Control y verifica que las dos colas se hayan detenido antes de
reiniciar sus punteros.

El [banco EDU](../tools/boot/amdvi_edu.py) ejecuta la rutina tras EBS.
Comprueba la transferencia traducida, el rechazo fuera de rango, la
revocacion y el cierre. La variante global comprueba tambien IASup.
Las contrapruebas distinguen la falta de IOMMU y una traduccion que
sigue en cache si se omite la invalidacion al revocar. En la placa
aun queda integrar la propiedad de los solicitantes activos con esta
rutina antes de conceder DMA al Falcon.

La [sesion fisica de traduccion](../kernel/drivers/bus/amdvi/physical_translation.S)
combina la publicacion reversible y la activacion. Usa el dominio
preparado de `2B:00.3` durante un ensayo xHCI y conserva las bases
originales hasta confirmar el cierre. Un fallo sin restauracion
confirmada mantiene las reservas fijadas. El banco HOST ejecuta la
rutina nativa de 1633 bytes contra registros simulados. Comprueba la
confirmacion y cierre, el rechazo sin IASup, el plazo vencido y la
retencion al producirse un evento de error.

El perfil de laboratorio `--amdvi-physical-usb-test` conecta esa sesion
al arranque del xHCI `2B:00.3`. La activa despues del reset y antes de
publicar las colas USB. Para pasar exige las dos paradas de
almacenamiento de ese arranque, comprueba PCI Command en vivo y
confirma la primera orden No-Op sin eventos AMD-Vi. El cierre comprueba
HCHalted y el retiro de Bus Master antes de devolver las bases
originales. La pagina adicional para el alias de CPU queda fuera de
los dominios DMA. El perfil prueba la exclusion de la ruta fisica en
QEMU y no emite medio FAT32 de despliegue.

El arranque fisico con `4e3c07d` mostro `USB 212 LPC 501 FWSEC 000`.
El primer No-Op bajo AMD-Vi y los controles del puente quedaron
confirmados. El estado cero de FWSEC no distinguia las guardas que
podian impedir la apertura.

La etapa NVIDIA ahora espera el No-Op traducido y comprueba el dominio
limitado de FWSEC. Relee en PCI identidad, BAR0, Command y estado PCIe
de `29:00.0`. Con Bus Master apagado, abre un alias supervisor de cinco
paginas de BAR0 y prepara Falcon. Solo entonces habilita Bus Master y
llama al cargador firmado. Retira el alias al volver y restaura PCI
Command en todas las salidas posteriores a la
apertura. Si hay transacciones PCIe pendientes cuando vence el plazo o
falla la lectura de vuelta, conserva la traduccion y fija las reservas.
UEFI reserva una pagina LoaderCode independiente para esta etapa. QEMU
comprueba la reserva y exige que la secuencia fisica quede excluida.

El estado de lanzamiento en `0x990` registra `400` si la prueba se rechaza,
`401` si el cargador confirma WPR2, `402` si falla DMA, `403` si falla la
ejecucion de Falcon o WPR2, y `404` si no se confirma el cierre PCIe.
`405` indica ausencia de la pagina de codigo, `406` dominio o sesion
sin confirmar, `407` identidad PCI o reloj invalidos, `408` PCIe no listo
y `409` alias BAR0 no disponible. `40A` indica rechazo previo al reset,
`40B` indica apertura de Bus Master sin confirmar.
El arranque fisico con `fec88fa` mostro `USB 212 LPC 501 FWSEC 40C`.
Confirmo la entrada al intento de reset con el dominio FWSEC ya validado.
En GA102, la espera previa de hasta 150 us consulta la senal de reset
completo. Tras el pulso, se verifica la salida del reset y se espera
por separado que termine la limpieza de memoria. El arranque con
`972c102` supero ambos pasos en METAL (`USB 212 LPC 501 FWSEC 413`).
La seleccion de Falcon se comprueba despues del reset y la limpieza,
porque el reset puede volver a seleccionar RISC-V. Si hay que cambiar
el selector, se exige `VALID` por lectura. Se conserva la exigencia
`HALTED` y `ACTIVE_STAT=0` antes del reset. Tras el reset y al cargar
FWSEC se exige Falcon seleccionado y `ACTIVE_STAT=0` en una lectura
valida. El estado `HALTED` pertenece al nucleo RISC-V.
`410` indica fallo en la seleccion, `411` en el pulso de reset,
`412` en la limpieza o `413` en el estado RISC-V posterior. Para esos
cuatro resultados, el escritorio recupera las lecturas CPUCTL y BCR
tomadas con el alias supervisor antes de retirarlo.
La captura de Falcon en `0x998` conserva la fase y los registros incluso
en caso de cierre incierto. En `427281f` el arranque fisico mostro el gato
y no llego al escritorio. `GPULOG.TXT` confirma la etapa UEFI, anterior
a la prueba FWSEC. La revision del codigo encontro que la lectura
del resultado `SCRATCH14` (BAR0+`0x1438`) caia fuera del alias supervisor.
La pagina BAR0+`0x1000` queda ahora incluida en el alias y se retira junto
con las otras cuatro. Los permisos DMA del dispositivo siguen en su
tabla separada. La prueba fisica de `2cf10f6` muestra
`USB 212 LPC 501 FWSEC 401` con escritorio visible. Eso acredita WPR2
y el cierre del Bus Master temporal de la RTX.

Para SEC2, HOST desglosa `booter_load` y `booter_unload` de la release
`615.78.08` comprobada por SHA-256. Cada entrada conserva los bytes
originales y define los rangos IMEM y DMEM, BOOTVEC, destino SEC2 y
ubicaciones de las firmas de produccion. QEMU coteja esos rangos con los
binarios reubicados cuando el manifiesto los incluye. El preparador HOST
`python -m tools.host.gpu.NVIDIA.sec2_booter` recibe el valor crudo del
fusible SEC2 y genera una copia DMA alineada. Con el valor cero elige
la ultima firma; para una version positiva resta la version del fusible
a la del booter y exige un indice valido. Conserva los offsets de ucode
y solo sustituye la ranura de firma en DMEM. La siguiente
prueba fisica debe cargar el booter firmado y confirmar su respuesta
en los buzones antes de lanzar GSP-RM.
[Formato y preparacion de booter GA102 en Nouveau](https://codebrowser.dev/linux/linux/drivers/gpu/drm/nouveau/nvkm/subdev/gsp/ga102.c.html#42).
[Seleccion de firma de booter en Nova](https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/nova-core/firmware/booter.rs).
[Mapa de registros PCIe Device Status](https://codebrowser.dev/linux/linux/include/uapi/linux/pci_regs.h.html#532).
[Secuencia de preparacion y limpieza de Falcon GA102 en Nouveau](https://codebrowser.dev/linux/linux/drivers/gpu/drm/nouveau/nvkm/falcon/ga102.c.html#70).
[Seleccion de Falcon y estado RISC-V en el controlador abierto de NVIDIA](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/src/nvidia/src/kernel/gpu/falcon/arch/ampere/kernel_falcon_ga102.c).

`--physical-fwsec-trial` genera el candidato separado
`EFI/BMO-X2/RTX-FWSEC.EFI` y sus datos en `BMO-X2/GPU-FW`. El instalador
exige `-PhysicalFwsecTrial -AmdviMmio -NvidiaProbe -ExperimentalUsb`, las
exclusiones de hardware verificadas en QEMU y la lectura del recibo en
Ring 3. Puede registrarse como `BMO-X2 (RTX FWSEC)` con la misma opcion
en `register-desktop.ps1` junto con `-AmdviMmio -NvidiaProbe`. El candidato
preexistente conserva sus rutas. La linea `RTX` del escritorio muestra
los recibos USB, LPC y FWSEC despues de iniciar el transporte xHCI. Si
la admision se rechaza, tambien muestra el BDF bloqueante. `FWSEC 401` acredita WPR2 con DMA PCIe
cerrado. El escritorio sigue usando GOP y el GPULOG de FAT32 se escribe
antes de EBS.

La [tabla FWSEC de la RTX](../kernel/drivers/bus/amdvi/fwsec_domain.S)
dedica dos paginas al dominio del solicitante `29:00.0`. Tras verificar
el FWSEC preparado, solo expone sus quince paginas de lectura en
`0A107000` a `0A115FFF`. El audio de la RTX conserva el dominio de
denegacion. El arbol que contiene GSP, colas y LIBOS queda separado.
Si FWSEC no esta listo, la funcion grafica conserva un dominio sin paginas.
El armado de esta tabla ocurre antes de abrir Bus Master.
[Especificacion AMD-Vi, permisos de lectura y escritura](https://docs.amd.com/api/khub/documents/GD6kOXjzWsek8QUbn_qMvg/content).

El inventario fisico anterior muestra `00:14.3` (`1022:790E`, puente
ISA) con Command `000F`. ULTRA-LinuX lo registra con SMBus `00:14.0`
en el grupo IOMMU 12. El perfil verifica el checksum ACPI y exige que
la firma, revision, longitud y todo el cuerpo de la IVRS coincidan con
la medida en el equipo, incluida la cobertura de ambos por `00:00.2`,
y vuelve a verificar clase, revision `51` y subsistema `1462:7C52`.
El arranque fisico con `10d4649` mostro `USB 215 LPC 503 FWSEC 000`
y `00:14.3`: el intento de limpiar Bus Master de Command no se confirmo.
AMD documenta ese bit como solo lectura para `1022:790E`. El candidato
usa los controles LPC del mismo ID: detiene el DMA legado en `0x40[2]`,
cierra las entradas LDRQ en `0x78[3:2]` y confirma ambos por lectura.
Consulta el motor de copia ROM en `0xB8[0]` antes y despues del cambio,
sin escribir ese registro. La tabla mantiene ambos FCH en el dominio
de denegacion. Los bits LPC se restauran tras un cierre confirmado o
una apertura revertida. Un estado AMD-Vi incierto mantiene los bits
apagados.

El recibo LPC distingue `501` (controles cerrados), `502` (restaurados),
`503` (cierre sin confirmar, restauracion confirmada), `504` (copia ROM
activa o registro no legible), `505` (control LPC no legible o semaforo
ocupado) y `506` (restauracion sin confirmar). El BKDG describe una
familia AMD anterior con ese ID. La respuesta de estos controles en la
revision `51` requiere confirmacion en METAL.
Los codigos `510` a `514` indican, en orden, un ID PCI, PCI Command,
cuerpo IVRS, clase/revision PCI o identificador de subsistema distinto.
Los solicitantes con BME sin una ruta admitida dejan su BDF en el
recibo y bloquean la activacion.
La tabla fisica usa DTE.I=0 y, por tanto, bloquea direccion ya
traducida por los dispositivos.
[Especificacion AMD IOMMU, tabla 7](https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/specifications/48882_IOMMU.pdf).
[AMD BKDG 55072, seccion 2.17.4.1 y registros D14F3](https://www.amd.com/content/dam/amd/en/documents/archived-tech-docs/programmer-references/55072_AMD_Family_15h_Models_70h-7Fh_BKDG.pdf).
[Inventario PCI en METAL](../Reports/dma-pci-census-metal-20261120.json).
[Estado de los discos en METAL](../Reports/storage-state-metal-20261120.json).
[Evidencia del candidato de cierre](../Reports/amdvi-storage-handoff-20261121.json).
[EFI Stall](https://uefi.org/specs/UEFI/2.10_A/07_Services_Boot_Services.html#efi-boot-services-stall).

El perfil QEMU `--amdvi-storage` agrega un AHCI virtual en un
tercer dominio. Ring 0 instala su tabla de traduccion. HOST
envia `READ DMA EXT` contra un disco de prueba, coteja 512 B
en la pagina fisica autorizada y verifica informes USB antes
y despues de revocar la pagina de EDU. El disco de prueba
conserva su contenido. Para llevar este mecanismo al equipo
AMD, falta cubrir los BDF de sus buses, validar las reservas
de DMA de los controladores que siguen en servicio y probar
la lectura de almacenamiento real bajo traduccion.
[Evidencia de almacenamiento e HID con AMD-Vi en QEMU](../Reports/amdvi-ahci-qemu-20261120.json).

El perfil `--amdvi-nvme` suma un cuarto dominio para NVMe `00:09.0`.
El ensayo `run-rmlui-media-643d37a4d77f` paso los tres casos QEMU.
Tras retirar las colas de OVMF con un cierre normal, el banco prepara
colas administrativas y de I/O nuevas. Ring 0 instala cinco paginas
IOVA traducidas para esas colas y el buffer de datos. QEMU qtest
programa el controlador. Comprueba el identificador y estado de cada
completado, el sector de 512 B en el respaldo fisico, la RAM testigo
de las IOVA intacta y cero fallos nuevos de AMD-Vi durante las lecturas.
AHCI, NVMe y USB pasan en la misma ejecucion de AMD-Vi. El banco
repite las lecturas tras revocar EDU y confirma el cierre del NVMe
antes de retirar su permiso PCI. El perfil solo emite imagen QEMU.

La reserva total del ensayo es de 31 paginas. Cinco alojan colas y
datos NVMe, cinco son testigos IOVA y tres forman sus tablas AMD-Vi.
El almacenamiento nativo aun requiere trasladar el control de las
colas fuera de qtest y comprobarlo en el equipo fisico.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist --amdvi-guest-dma --amdvi-storage --amdvi-nvme
```

[Evidencia de NVMe traducido](../Reports/amdvi-nvme-qemu-20261120.json).
[Especificacion de colas NVMe](https://nvmexpress.org/specification/nvme-express-base-specification/).

El perfil `--amdvi-guest-nvme` traslada la creacion de las colas y la
lectura NVMe a Ring 0. Revalida el dispositivo y su BAR, limita la
ventana MMIO a dos paginas UC de supervisor, y usa el dominio 4 para
crear CQ1/SQ1 y leer el LBA 8. El laboratorio solicita esta operacion
fija. Ring 0 coteja los tres completados, espera el cierre normal,
retira BME y revoca la ventana temporal.

QEMU manda el numero de operacion y verifica que los completados y
los 512 B de salida aparezcan en el respaldo traducido. El escenario
rechaza la lectura sin dominio y con EDU todavia habilitado para DMA.
Los dos ensayos positivos conservan los informes HID y verifican los
mismos datos. El cierre inicial de OVMF y el manejo de SATA siguen en
qtest en este banco. Queda validar en METAL las colas y los dominios
antes de arrancar el GSP.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist --amdvi-guest-dma --amdvi-storage --amdvi-nvme --amdvi-guest-nvme
```

[Colas NVMe del invitado y registro METAL](../Reports/amdvi-guest-nvme-qemu-20261120.json).

El perfil `--amdvi-guest-ahci` completa el traspaso de los dos discos
virtuales desde Ring 0. Con AMD-Vi apagado, NVMe confirma su cierre
normal y AHCI detiene los motores de sus seis puertos. Solo entonces
se retira BME de cada controlador. Con AMD-Vi activo, el invitado lee
el sector de prueba en los dominios independientes 3 y 4 y vuelve a
retirar BME. Las reservas se retienen ante un fallo.

El banco solicita las operaciones fijas, suspende otros solicitantes
emulados y comprueba los registros, los datos y los testigos de cada
IOVA. El ensayo verifica teclado y raton tras las lecturas. Los medios
de este perfil quedan confinados a QEMU. La RTX y los discos fisicos
requieren su propio traspaso y verificacion.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist --amdvi-guest-dma --amdvi-storage --amdvi-nvme --amdvi-guest-nvme --amdvi-guest-ahci
```

[Traspaso y lecturas de Ring 0 en QEMU](../Reports/amdvi-guest-storage-qemu-20261120.json).
[Especificacion AHCI 1.3.1](https://www.intel.com/content/www/us/en/io/serial-ata/serial-ata-ahci-spec-rev1-3-1.html).

El perfil `--amdvi-routed` agrega un dispositivo EDU detras de un
puerto PCIe en un bus alto. Ring 0 descubre el BDF completo, valida
la reserva UEFI y programa 512 paginas (2 MiB), suficientes para cubrir
los 65,536 valores DTE de `0000` a `ffff`. En
`run-rmlui-media-29fb2cbe0ef2` verifica todas las entradas restantes
contra la raiz vacia de denegacion, instala dominios independientes para
EDU `29:00.0`, xHCI `00:05.0` y AHCI `00:06.0`, e invalida los 12
solicitantes presentes. La transferencia DMA de EDU funciona solo dentro
del rango concedido; el testigo fuera de rango permanece igual y la
revocacion cierra la transferencia sin interrumpir teclado, raton o SATA.
Los otros dos casos rechazan W+X y AMD-Vi ausente. Los tres pasaron.
El evento de QEMU puede informar solo dispositivo y funcion para una
solicitud fallida de otro bus; el informe conserva esa limitacion y coteja
el BDF completo por separado. El perfil es exclusivo de QEMU y no concede
DMA a la RTX fisica.
[Prueba DMA con tabla completa](../Reports/amdvi-full-dte-default-deny-qemu-20261121.json).

El HOST coteja tambien la tabla IVRS actual contra el censo METAL archivado:
```powershell
$py = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py -B tools/host/gpu/ivrs.py --census-json Reports/dma-pci-census-metal-20261120.json --output-json Reports/amdvi-physical-dma-preflight-20261121.json
```
El resultado cubrio los 17 BDF registrados y encontro 15 con Bus Master
activo; la RTX `29:00.0` (`10de:2504`) aparece con Bus Master apagado.
Ningun dominio queda marcado como verificado y la herramienta
siempre niega permiso de traduccion: la cobertura IVRS no acredita DTE,
quiesce, invalidacion ni limites DMA. El censo fisico tiene que actualizarse
si cambia el hardware o su configuracion antes de usarlo como plan.
[Preflight de solicitantes DMA](../Reports/amdvi-physical-dma-preflight-20261121.json).

Antes de activar la traduccion en METAL hay que bloquear los
solicitantes sin dominio. Una DTE a cero deja V desactivado y
AMD-Vi puede encaminar la solicitud sin traducir. El perfil
PCIe virtual instala una DTE valida con una raiz vacia para
cada solicitante no admitido e invalida todas las DTE presentes.
El segundo EDU verifica la misma
escritura antes y despues de activar AMD-Vi. Durante la
traduccion debe aparecer el fallo y quedar intacto el testigo.
[Bloqueo por defecto en QEMU](../Reports/amdvi-default-deny-qemu-20261120.json).
[Interaccion V y TV en AMD-Vi](https://docs.amd.com/api/khub/documents/GD6kOXjzWsek8QUbn_qMvg/content).
[Invalidacion de entradas en QEMU](https://github.com/qemu/qemu/blob/master/hw/i386/amd_iommu.c).

El primer patron usa como referencia el triangulo de
[C++ / MSVC](../tools/tests/msvc_desktop_panel.cpp). El panel actual
genera los pixeles con CPU. Para el ensayo NVIDIA, el cliente C++ de
Ring 3 enviara el trabajo a un buffer fuera de pantalla. El resultado
leido de la GPU se cotejara con la referencia antes de presentar por
el conector NVIDIA.
[Panel C++ validado en QEMU](../Reports/abi-msvc-rmlui-qemu.json).

La presentacion NVIDIA y la lectura de sensores tienen ritmos
distintos. El backend de salida debe publicar el conector, modo,
refresco y confirmacion de presentacion. Ring 3 podra consultar por
separado temperatura, uso y VRAM, con un intervalo mayor durante
juegos para que el sondeo quede fuera del camino de cada cuadro.

La captura posterior usa los estados `01` (sin captura previa usable),
`02` (mapeo, PAT o mapa de memoria rechazado), `03` (base PCI
modificada), `04` (cinco registros leidos) y `05` (MMIO devolvio
todo unos). INVOKE acepta solo los seis indices fijos del informe.
Ring 0 coteja la base PCI y el mapa UEFI final, verifica el tipo UC
de PAT y abre dos paginas supervisoras de solo lectura y NX. Retira
ambas con `INVLPG` antes de inicializar xHCI. Los registros se muestran
en el pie del escritorio y en la serie QEMU como `AMDVI_POST=`.
[Paginacion y PAT de AMD64](https://docs.amd.com/v/u/en-US/24593_3.44_APM_Vol2).

`run-rmlui-media-61ebf6ff6e23` paso tres arranques en QEMU.
El caso normal cotejo los cinco registros entre UEFI y Ring 0, los
permisos de las dos entradas y la continuidad del escritorio USB.
El arranque sin AMD-Vi mostro `01` y abrio cero paginas. El cargador
conservo el rechazo W+X. El paquete de entrada ocupa 4032 B y la
sonda posterior ocupa 530 B dentro de una pagina ya reservada.
[Evidencia de la captura posterior](../Reports/amdvi-post-ebs-desktop-qemu-20261120.json).

En el equipo de referencia, el inventario HOST da IVRS `000000D0`,
BDF `00000002` y base `FD500000` al enmascarar el bit de habilitacion.
El candidato con la sonda se arranca desde la entrada existente
**BMO-X2 (con NVIDIA)**. Al volver a Windows, leer `GPULOG.TXT` y
comprobar que contiene las lineas `AMDVI=` y `AMDVI_MMIO=` del
nuevo arranque. El 20-11-2026 se verifico la copia de
`run-rmlui-media-61ebf6ff6e23` en `A:`, con respaldo del EFI
NVIDIA anterior, INICIO.X86 y DESKTOP.SBF de ese perfil. La captura
posterior se lee junto a `AMD-Vi Ring 0` en el pie del escritorio.

La ruta de aceleracion y control de salida vive en `GPU/NVIDIA`.
DIRECTOR/RmlUi entrega superficies a traves de la capacidad de pantalla.
El supervisor concede al controlador solo los recursos de su dispositivo
y sus buffers. La salida tiene un solo dueno durante la sesion. La
entrega suspende GOP antes de activar el control de salida NVIDIA.
Se conserva CPU + GOP mediante la entrada UEFI del escritorio base.
Una recuperacion en caliente requerira una prueba propia de restauracion
del modo de pantalla. El informe de la ruta NVIDIA debe exponer el
backend activo, conector, modo y fase de fallo.

El ensayo `run-rmlui-media-00741e5f358f` verifica una VGA de clase 03,
cero funciones NVIDIA, el escritorio y el rechazo W+X. El resultado se
recupera del FAT32 como `build/puente-normal-GPULOG.TXT`. En ese ensayo
la sonda agrego 298 B al lector dentro de la pagina EFI reservada.
El paquete `INICIO.X86` y el escritorio SBEF coinciden byte por byte
con el perfil PS/2 sin sonda. Para construir y abrir el perfil se usan
los mismos runs ABI y gato que para el escritorio base.

El ensayo `run-rmlui-media-47240bf1c3fa` repite los dos casos con
`--usb both`. QEMU verifica teclado y raton USB juntos, y la revocacion
de bus mastering y MMIO al detener xHCI. El lector PCI sigue en la
misma ruta anterior a ExitBootServices.
El ensayo `run-rmlui-media-cf7403e99951` conserva el perfil USB dual y
coteja el inventario BAR con QMP. El lector del candidato pasa de 2814 B
a 3050 B dentro de la misma pagina EFI. El paquete CASM y el SBEF
conservan sus bytes. `GPULOG.TXT` pasa de 397 B a 504 B.

```powershell
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN> --nvidia-probe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-nvidia-probe
```

Para generar el candidato USB dual con inventario AMD-Vi:

```powershell
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe
```

Para incluir la captura posterior al traspaso:

```powershell
python .\tools\desktop\rmlui\native\guest.py --desktop --usb both --amdvi-post
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post
```

Para el candidato con inventario PCI, agregar `--dma-census` a las dos
ordenes del perfil `--amdvi-post`.
Para agregar la lectura AHCI/NVMe, pasar ademas `--storage-state` a
las dos ordenes.
Para dibujar a 1920x1080 nativos en GOP, pasar tambien `--full-hd` a
ambas ordenes.

`native/deploy.ps1 -Run <RUN> -Volume A:\ -NvidiaProbe -Check` comprueba
el candidato para METAL. Agrega `-ExperimentalUsb` para el run USB dual.
La copia explicita del perfil se hace con los mismos argumentos sin
`-Check`. Tras la copia, PowerShell 5.1 elevado permite registrar
**BMO-X2 (con NVIDIA)** al final del menu UEFI:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\native\register-desktop.ps1 -NvidiaProbe
```

El registro comprueba el recibo en A:, sus tres hashes y la prueba
QEMU del run. Si existe la misma entrada, la reutiliza. Al arrancar se
elige **BMO-X2 (con NVIDIA)**. En un firmware con **Boot from file**
tambien se puede abrir `\EFI\BMO-X2\NVIDIA.EFI` directamente. Cada
ensayo en METAL deja `A:\BMO-X2\GPU\GPULOG.TXT`.

### Primer triangulo giratorio

La RTX 3060 renderiza en Windows 48 cuadros RGBA8 de 480 por 360 con
Vulkan. El shader inclina el triangulo alrededor de un eje oblicuo y
proyecta cada cuadro en perspectiva. El exportador verifica los cuadros
y empaqueta una vuelta de 2,4 segundos como GIF. El ensayo de HOST usa
el controlador de Windows y sirve de referencia visual para METAL.

En un entorno x64 de MSVC, con Vulkan SDK y Python con Pillow:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\host\gpu\NVIDIA\triangle\run.ps1
```

La salida queda en `build/gpu/NVIDIA/triangle-host`. Para dibujar el
primer cuadro nativo, el perfil NVIDIA necesita adjudicar el dominio
DMA real, obtener respuesta del GSP y enviar trabajo a un canal grafico.
[Informe del triangulo](../Reports/nvidia-triangle-host-20261120.json).

La [codificacion de scanout para GA106](../userspace/drivers/GPU/NVIDIA/scanout.rs)
prepara los metodos de imagen C67E para una ventana que el canal core ya
vinculo a la salida. Los vectores HOST cubren 1280x720, 1920x1080 y un
segundo buffer de VRAM con pitch distinto. El modo y la frecuencia aun se
eligen fuera de este modulo. Para retirar GOP, la prueba en metal debe
presentar una superficie producida por la GPU, esperar la confirmacion de
NVIDIA en el canal de pantalla y comprobar el resultado en el monitor.
Referencias [NVDisplay](https://github.com/NVIDIA/open-gpu-doc/blob/master/classes/display/README.txt)
y [metodos de la ventana C67E](https://github.com/NVIDIA/open-gpu-doc/blob/master/classes/display/clc67e.h).

```powershell
rustc --edition 2024 --test userspace/drivers/GPU/NVIDIA/scanout.rs -o build/nvidia-scanout-tests.exe
.\build\nvidia-scanout-tests.exe
```

### Medir los tirones antes de cambiar el presentador

1. Repetir cuatro casos con la misma resolucion, escala y perfil de
   entrada: movimiento, paso sobre el boton, clic en Activar ULTRA-J y
   cambio de espacio. Registrar por evento la espera y entrega de entrada,
   la accion UJBC, el dibujo de RmlUi y el final de la copia a GOP.
2. Contar pixeles copiados, actualizaciones parciales y cuadros
   completos. Publicar p50/p95/p99 y el maximo por caso. La marca de fin
   de copia mide el recorrido interno. Medir hasta que el monitor muestra
   el cambio requiere una observacion adicional en hardware.
3. Empezar por el clic. QEMU ya verifica puntero y hover sin rasterizar
   el escritorio en el perfil USB dual. Un cambio de interfaz aun puede
   rasterizar y presentar toda la superficie del modo activo. Si domina esa
   fase, extender las regiones modificadas al boton y al panel con la
   capacidad de pantalla y sus comprobaciones. Si domina la espera,
   medir el despertar de entrada antes de ajustar el temporizador.

[Evidencia de puntero, hover y teclado](../Reports/abi-msvc-rmlui-qemu.json).
[Huella y reservas del escritorio](FOOTPRINT.md).

## Reproducir y copiar

Desde la raiz del proyecto, con los runs CASM verificados del ABI y del
gato compacto:

```powershell
python .\tools\desktop\rmlui\native\guest.py --desktop
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN>
python .\tools\desktop\rmlui\native\media.py <ABI_RUN> <GATO_COMPACTO_RUN> --low-gop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-desktop
```

Para copiar un run aprobado: `native/deploy.ps1 -Run <RUN> -Volume A:\`.
La herramienta valida el FAT32 existente, las pruebas y cada hash; omite
archivos identicos, copia solo el candidato y respalda la version anterior
en `fat32-backups` dentro del run del proyecto, sin llenar A: de respaldos.
Verifica
que los archivos de arranque antiguos no hayan cambiado. No formatea.
