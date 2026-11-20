# Prestamo y revocacion de DMA

El contrato previsto entrega al servicio una capacidad de transferencia.
Ring 0 vincula dispositivo, direccion DMA, permiso de lectura o escritura,
rango y propietario. El mapeo de IOMMU queda
acotado a los marcos concedidos. La CPU y el dispositivo tienen
traducciones independientes.

| Paso | Condicion para avanzar |
|---|---|
| Conceder | Validar dispositivo, capacidad, rango y direccion. Reservar los marcos y mapearlos en el dominio IOMMU. |
| Transferir | La cola acepta solo referencias a prestamos activos. El dispositivo confirma la finalizacion. |
| Cerrar | Detener nuevas solicitudes y confirmar la finalizacion o una parada efectiva del dispositivo. |
| Revocar | Retirar el mapeo DMA y confirmar las invalidaciones pertinentes. Retirar los mapeos CPU que pierden acceso y confirmar sus invalidaciones. |
| Reutilizar | Con todos los accesos cerrados, borrar si cambia el propietario y devolver al asignador. |

Si falla la confirmacion, el buffer sigue reservado y el diagnostico
registra el dispositivo y la fase. Si el equipo carece de aislamiento
DMA verificable, la ruta directa queda fuera del perfil de usuario.

La [prueba qtest](../../../Reports/nvidia-amdvi-qemu-20261120.json)
demuestra en el modelo AMD-Vi de QEMU una transferencia permitida, dos
rechazos de escritura (fuera del rango y despues de invalidar), y la
confirmacion de la invalidacion. El kernel invitado no interviene.
La retencion del buffer al fallar la revocacion requiere una prueba
nativa. El ensayo de revocacion de pagina cubre el TLB de una CPU.

La [sonda nativa EDU](amdvi/edu_probe.S) arranca desde FAT32 en CPL0
despues de ExitBootServices, reutilizando las tablas de CPU de OVMF.
Reserva nueve paginas UEFI contiguas (36 KiB) y concede solo una pagina
de DMA en AMD-Vi. El caso normal valida los bytes traducidos, dos
bloqueos de escritura y el cierre. El caso sin AMD-Vi termina antes de
programar DMA. Omitir la invalidacion conserva una traduccion antigua
en el modelo, y la sonda detecta la escritura y cierra bus mastering.
Los casos terminan el invitado de laboratorio y su memoria reservada.
El dominio fisico y la retencion en un kernel que sigue ejecutando quedan
pendientes. [Evidencia nativa QEMU](../../../Reports/amdvi-edu-native-qemu-20261120.json).

```powershell
python -B tools/boot/amdvi_edu.py
```

La [sonda UEFI de solo lectura](amdvi/firmware_probe.S) del perfil NVIDIA
registra IVRS y la base PCI antes de ExitBootServices. Esta captura separa
una unidad ausente, una base que difiere del firmware y el estado de
decodificacion MMIO. METAL confirmo la unidad `0000:00:00.2` con
decodificacion activa en `0xFD500000` y bus mastering de la RTX
apagado. El candidato ampliado lee control, tabla, bases de colas y
estado mediante CPU I/O 2. La sonda EDU comprueba esos registros al
entrar en CPL0 tras el traspaso y hace readback de control y bases
antes de conceder DMA virtual. El dominio fisico requiere una ventana
MMIO propia y una prueba despues del traspaso.
[Captura METAL](../../../Reports/nvidia-pci-metal-20261120-amdvi.json).

La captura MMIO en METAL confirma traduccion desactivada antes de
ExitBootServices, con las bases de comandos y eventos programadas
por encima de 4 GiB. La propiedad de esas paginas sigue por comprobar.
El ensayo siguiente comparo el estado despues del traspaso mediante
dos paginas MMIO de solo lectura y con permisos de supervisor. La
[sonda post-EBS](amdvi/post_ebs_probe.inc) reutiliza la tabla temporal
de xHCI antes de iniciar ese controlador. Revoca las dos entradas
antes de entregar los valores capturados a Ring 3.
[Registros en METAL](../../../Reports/nvidia-pci-metal-20261120-amdvi-registers.json).
[Cotejo antes y despues](../../../Reports/nvidia-pci-metal-20261120-amdvi-post-ebs.json).

La traduccion se habilita para la unidad AMD-Vi. Antes de cambiarla
se requiere un inventario de solicitantes activos con mapeos validos
o confirmacion de parada. El ensayo con EDU verifica que xHCI sigue
entregando eventos mientras se concede y revoca la pagina de prueba.
La comprobacion de almacenamiento fisico debe medir una
transferencia despues de ExitBootServices con la traduccion activa.

El perfil `--amdvi-coexist` agrega EDU al escritorio QEMU con USB
dual. Reserva 13 paginas EfiLoaderData para el ensayo. HOST configura
AMD-Vi con qtest mientras el invitado esta pausado. Concede una pagina
a EDU y las 14 paginas de la reserva USB al dominio xHCI. QMP inyecta
teclas y movimiento mientras EDU transfiere y despues de revocar su
pagina. La prueba es exclusiva de QEMU y conserva la ruta CPU + GOP.
Las operaciones de configuracion las emite HOST. El invitado sigue
ejecutando su driver USB habitual.
[Resultado QEMU](../../../Reports/amdvi-xhci-coexist-qemu-20261120.json).

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist
```

`--amdvi-guest-dma` ejecuta la configuracion dentro de Ring 0.
Antes de activar AMD-Vi, comprueba la reserva UEFI y el bus PCI del
invitado. Usa una segunda tabla temporal para MMIO, separada de la
de xHCI. Ring 0 instala las dos tablas, publica las invalidaciones,
espera sus confirmaciones y apaga la traduccion al cerrar el ensayo.
El HOST opera el EDU virtual, mantiene quietos los otros solicitantes
del laboratorio y verifica los resultados. El candidato permanece
exclusivo de QEMU.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist --amdvi-guest-dma
```

El ensayo del invitado rechazo la activacion con otro bus master
activo. Tras suspender los demas solicitantes virtuales, confirmo
ambos dominios, bloqueo DMA fuera de rango y despues de revocar,
y cerro AMD-Vi conservando USB. Recibio dos informes de teclado
y uno de raton en cada etapa de DMA. El modulo ocupa 1426 B y el
laboratorio reserva 14 paginas para sus tablas, colas y testigos.
[Evidencia del invitado](../../../Reports/amdvi-xhci-guest-qemu-20261120.json).

El perfil `--amdvi-storage` mantiene el banco virtual y agrega
el dominio 3 para AHCI `00:06.0`. Ring 0 concede una pagina con
IOVA distinta del respaldo fisico. Las cuatro paginas adicionales
reservan raiz, hoja, buffers AHCI y memoria testigo para la IOVA.
HOST arma y detiene el puerto AHCI emulado. Comprueba el sector
leido, el contador de bytes, el testigo intacto y la ausencia de
fallos IOMMU durante las dos lecturas. La segunda lectura ocurre
despues de invalidar EDU. Ambas pruebas reciben informes HID.

```powershell
python -B tools/desktop/rmlui/native/media.py <ABI_RUN> <GATO_COMPACTO_RUN> --usb both --nvidia-probe --amdvi-probe --amdvi-post --amdvi-coexist --amdvi-guest-dma --amdvi-storage
```

[Evidencia AHCI en QEMU](../../../Reports/amdvi-ahci-qemu-20261120.json).
[Especificacion AHCI](https://www.intel.la/content/dam/www/public/us/en/documents/technical-specifications/serial-ata-ahci-spec-rev1-3-1.pdf).

El perfil `--amdvi-routed` permite comprobar la localizacion de una
DTE por un solicitante de bus alto. Reserva 96 paginas contiguas
para la tabla de dispositivos, cubriendo los indices PCI hasta
`2fff`, y conserva las otras 18 paginas para el ensayo. El
invitado recorre todo el segmento PCI, permite dos puertos raiz
del banco y obtiene el BDF de EDU de la configuracion PCI.
El banco coteja el BDF con QMP, la entrada de dominio en RAM,
el comando de invalidacion y los testigos de DMA autorizado,
fuera de rango y revocado. La segunda lectura SATA y los
informes HID conservan sus comprobaciones.

[Prueba del solicitante PCIe de bus alto](../../../Reports/amdvi-routed-qemu-20261120.json).
[Formato de la tabla de dispositivos AMD-Vi](https://docs.amd.com/api/khub/documents/GD6kOXjzWsek8QUbn_qMvg/content).

El perfil `--dma-census` usa la operacion de diagnostico
`INVOKE(3, 3, 26, indice)`. El indice 0 congela la primera captura
y entrega el encabezado. De menor a mayor bit, contiene el numero
de filas (16 bits), el BDF xHCI (16 bits, `FFFF` si queda sin
controlador) y el total PCI con BME (32 bits). Los indices 1 a
`2 * filas` entregan dos palabras de 64 bits por fila. La primera
empaqueta BDF, PCI Command, Vendor ID y Device ID en cuatro campos
de 16 bits. La segunda contiene el codigo de clase PCI de 24 bits.
Los indices fuera de rango devuelven 257. El perfil consulta el
segmento 0 en orden BDF y deja los registros de cada funcion intactos.
[Prueba de captura y panel](../../../Reports/dma-pci-census-qemu-20261120.json).
[Inventario fisico y cobertura IVRS](../../../Reports/dma-pci-census-metal-20261120.json).

El puente del escritorio reserva cinco paginas contiguas de EfiLoaderData
por debajo de 256 MiB y las entrega en los campos B8/C0 del contexto.
La variante QEMU de comandos agrega una pagina para contextos
y cuatro para scratchpads (40 KiB en total). Ring 0 valida toda la reserva y prepara
una tabla de direcciones fisicas alineadas. Publica la tabla en
DCBAA[0] solo si HCSPARAMS2 solicita scratchpads y aborta antes de
activar el controlador si solicita mas de cuatro.
El run `run-desktop-media-1c740af27864` comprueba 20480 bytes a cero,
la cobertura por el mapa UEFI y la separacion del contexto y el codigo.
El perfil normal conserva la reserva en blanco. La variante
`stage_desktop_media.py --xhci-command` usa esa reserva con qemu-xhci
para un comando No Op y coteja el TRB de finalizacion. Comprueba parada,
restauracion del registro PCI Command y retiro de las paginas MMIO.
Con un usb-kbd emulado tambien restablece el puerto, asigna una ranura,
direcciona el dispositivo y lee su descriptor de 18 bytes por EP0.
La misma sonda lee la configuracion de 34 bytes, valida una interfaz
HID boot, solicita SET_CONFIGURATION y SET_PROTOCOL y configura
el endpoint 1 IN. QEMU inyecta F2 y F3, con sus flancos de liberacion.
La sonda rearma cuatro posiciones fijas y verifica el retorno al
inicio de las colas de transferencias y de eventos con 260 informes
antes del cierre de sesion.
WAIT comprueba el evento al despertar del PIT. INVOKE valida el TRB
y entrega el informe a Rust. QEMU comprueba que CABINA abre con el
controlador activo y que este se detiene al ejecutar `session exit`.
La variante `--usb-mouse` usa las mismas colas con el tamano anunciado
por el endpoint y acepta reportes cortos con al menos tres bytes.
Ring 3 adapta botones y desplazamientos HID a su flujo de puntero.
QEMU coteja el informe recibido, la posicion del cursor y el foco.
La etapa se guarda bajo `qemu-only`. Antes de programar las colas,
Ring 0 exige que las diez paginas tengan cobertura exclusiva de
EfiLoaderData y esten separadas del contexto, del paquete y del SBEF.
Si la parada no se confirma, la sonda
intenta desactivar bus mastering y conserva las paginas reservadas.

La comprobacion acota las direcciones que el controlador recibe del
driver. La proteccion frente a un dispositivo que accede fuera de
esas direcciones requiere que el hardware aplique un dominio IOMMU.
El contrato comun de prestamos define propiedad, direccion y
revocacion. AMD IOMMU e Intel VT-d son posibles implementaciones
de ese contrato. Quedan pendientes esos dominios, la enumeracion
simultanea y la recuperacion de dispositivos tras desconexion.
Para el futuro reciclador, conservar la regla de propiedad explicita:
reutilizar una posicion cuando llega su finalizacion y liberar las paginas
de la sesion tras confirmar la parada del controlador.

[Especificacion xHCI, seccion 4.10.1.1.2](https://cdrdv2-public.intel.com/625472/625472_xHCI_Rev1_2b.pdf)

QEMU pide cero scratchpads. La prueba coteja las cuatro direcciones
de la tabla, las paginas a cero y DCBAA[0] a cero. Queda probar el uso
real de scratchpads. Los desplazamientos de los contextos se
calculan con el tamano anunciado. QEMU ejercita el formato de 32
bytes con teclado full-speed y high-speed. Queda validar 64 bytes
con un controlador que anuncie ese formato.

[Revocacion de pagina](../../mm/virtual/revoke/HOT-UNMAP.md) |
[Referencia de DMA en Linux](https://docs.kernel.org/core-api/dma-api-howto.html)
