# Candidato de escritorio RmlUi desde FAT32

El candidato une el motor RmlUi/FreeType, el dibujo Rust y la politica
DIRECTOR existente de Rust. Es un panel ULTRA-J con espacios y cierre,
no la migracion completa de CABINA, DOOM y todas las aplicaciones.
El arranque anterior se conserva para esas funciones.

## Que esta comprobado

- QEMU arranca el gato compacto CASM y lee el SBEF desde FAT32 mediante
  UEFI. No se inyecta un modulo con `-device loader`.
- Antes de ExitBootServices se reserva el rango privado de usuario de
  16 MiB en 04000000h, con propiedad registrada. El cargador comprueba
  esa reserva y el mapa antes de escribir alli; no usa RAM supuesta libre.
- El lector tiene un perfil explicito de hasta 2 MiB. El limite de
  16,512 bytes del escritorio anterior no se amplia silenciosamente.
- El archivo INICIO.X86 sigue cabiendo en la pagina de 4 KiB. Se utiliza
  el gato compacto, porque el HD y esta entrada excederian ese limite.
- DIRECTOR decide foco, espacios, movimiento y cierre. La superficie
  1x1 que usa su adaptador es solo un marcador de politica: no comparte
  como referencia Rust el framebuffer mutable propiedad de C++.
- El presentador acepta la superficie logica 1280x800. En GOP menores
  usa una vista 640x400; en los mayores usa escala entera y centrado.
  QEMU verifica los pixeles del camino normal y del GOP 1024x768.
- Se prueban Enter, clic PS/2, espacios, cierre, reapertura y rechazo
  W+X antes de copiar codigo. Se vuelve a leer el BOOTLOG de la imagen
  FAT32 y se compara el SBEF del disco con el ejecutable esperado.

El heap sigue acotado a 4 MiB y el framebuffer ocupa 4,096,000 bytes.
El candidato mide 1,845,846 bytes de SBEF; el pico medido de su heap es
3,050,544 bytes. Las pruebas y huellas quedan conservadas en
[la evidencia del candidato](../Ultra-J/evidence/rmlui-desktop-fat32.json).
El mapeo privado de 16 MiB incluye la pila. No equivale al peso total
del nano-core ni demuestra que todo BMO-X2 consuma 2 KiB.

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
arranque. [Verificacion HOST](../tools/host/gpu/firmware.py).
[Procedencia de 570.144 en linux-firmware](https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/%2B/refs/tags/20250917/WHENCE).
[GSP 615.78.08 de NVIDIA](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/gsp.html).

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
python -B tools/host/gpu/firmware.py native ..\BMO-externo\firmware\nvidia\ga102\gsp
python -B tools/host/gpu/firmware.py 570.144 ..\BMO-externo\firmware\nvidia\ga102\gsp
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
apuntadas y el estado posterior al traspaso quedan por comprobar.
[Captura de registros en METAL](../Reports/nvidia-pci-metal-20261120-amdvi-registers.json).

Siguientes pruebas y criterio de avance:

1. Usar la base verificada por IVRS y PCI para repetir la lectura en
   Ring 0 despues de ExitBootServices. Mapear solo las paginas que
   contienen los cinco registros como MMIO supervisor, no ejecutable,
   sin cache y de solo lectura. Probar en QEMU la lectura y el rechazo
   sin unidad o sin mapeo. En METAL, cotejar los dos estados.
2. Probar el dominio DMA fisico de la RTX y su funcion de audio
   conservando la operacion de USB y almacenamiento. Acreditar acceso
   concedido, rechazo fuera del rango y revocacion confirmada. Retener
   las paginas si falla la invalidacion. Reservar tablas y colas propias
   antes de configurar la traduccion. El log pre-EBS ya muestra dos
   controladores xHCI con bus mastering habilitado.
3. Arrancar GSP `615.78.08` con los buffers autorizados y verificar
   una respuesta valida. Luego ejecutar una operacion sobre un buffer
   dedicado, comprobar su salida y demostrar dibujo 3D fuera de
   pantalla antes de entregar el conector al backend NVIDIA.
[Contrato DMA](../kernel/drivers/bus/DMA.md).

En el equipo de referencia, el inventario HOST da IVRS `000000D0`,
BDF `00000002` y base `FD500000` al enmascarar el bit de habilitacion.
El candidato con la sonda se arranca desde la entrada existente
**BMO-X2 (con NVIDIA)**. Al volver a Windows, leer `GPULOG.TXT` y
comprobar que contiene las lineas `AMDVI=` y `AMDVI_MMIO=` del
nuevo arranque. El 20-11-2026 se verifico la copia de
`run-rmlui-media-a3d1dd3a0584` en `A:`, con respaldo del EFI
NVIDIA anterior y sin cambiar el orden de arranque.

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
   rasterizar y presentar toda la superficie de 1280x800. Si domina esa
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
