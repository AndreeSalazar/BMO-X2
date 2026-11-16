# REPORTES

Entrada a los diagnosticos de BMO-X2. El perfil de escritorio `-Reports`
muestra automaticamente motivo, siguiente paso y pulsos obtenidos por
INVOKE de Ring 0. No requiere teclado ni raton. El aviso inferior conserva
la fase exacta USB y el censo de puertos. El color amarillo significa un
hito parcial: ni DMA OK ni descriptores leidos acreditan entrada HID.

Codigo: [panel](../tools/desktop/reports.rs),
[exportador HOST](../tools/boot/report.py). Evidencia QEMU en
[evidence.json](evidence.json).

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1 -Session -External -Reports -AbiRun build/CASM/run-20261112-174958-944cb997
# Como tercer argumento se utiliza un run desktop-external ya comprobado.
$reportPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $reportPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-ab5e8222cf60 --xhci-enum-probe --reports-desktop build/desktop/desktop-reports.sbef --ram-mib 256
```

La vista vive en Ring 3. Consulta los contadores al despertar, con WAIT
de hasta 25 pulsos PIT, y vuelve a dibujar el panel cuando cambia la fase
o se restaura el escritorio. Actualiza solo los digitos del reloj durante
la espera. No es una garantia de tiempo real duro. La sonda USB actual
es sincrona: sus fases internas no se muestran hasta que INVOKE retorna.

Este perfil dedica el espacio de F3/configuracion a REPORTES para conservar
el limite de 8192 B RX. El escritorio normal mantiene su configuracion.
CABINA F2 sigue disponible cuando la entrada funciona.

Para conservar resultados legibles en esta carpeta:

```powershell
$reportPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $reportPython -B tools/boot/report.py build/CASM/RUN_COMPROBADO
```

`latest.txt` y `latest.json` separan QEMU, BOOTLOG UEFI y resultado fisico
posterior. El exportador corre en HOST y solo lee A:. El log V3 actual no
contiene eventos posteriores a ExitBootServices. El panel tampoco escribe
FAT32: faltan transporte de bloques, escritor de archivos y cierre seguro
para persistir registros del runtime. Las excepciones fatales que impidan
ejecutar Ring 3 requieren ademas una salida de emergencia de Ring 0.

El panel inicial cubre entrada USB y contadores disponibles. RAM, todos
los dispositivos y un historial general de fallos aun necesitan contratos
y productores de diagnostico propios; no se inventan a partir de estos
contadores.

## Detalle EP0

La foto anterior en AMD alcanzo `USB EP0 CABECERA`, con tres puertos
conectados. Eso acredita Address Device, pero no permite distinguir
timeout, terminacion de error, cabecera o MPS invalido. La version actual
publica Setup solo despues de preparar Data y Status, con barreras de
escritura antes de ceder el TRB y antes de tocar el doorbell. La secuencia
se contrasta con [xhci_queue_ctrl_tx de Linux](https://github.com/torvalds/linux/blob/master/drivers/usb/host/xhci-ring.c).
La causa del fallo AMD previo aun no esta confirmada.

Los detalles se muestran en hexadecimal, sin modificar el resultado:

| Campo | Significado |
|---|---|
| P / S | Puerto raiz y ID de velocidad observado. |
| CC | Codigo del ultimo evento recibido. 01 es exito; 06 es STALL. 00 con evento vacio significa que no se capturo una respuesta util. |
| LEFT | Residuo de longitud de 24 bits del evento; en un error no se interpreta como bytes recibidos validos. |
| REQ | Longitud solicitada para la transferencia actual. |
| MPS | Byte observado en bMaxPacketSize0; requiere cabecera de dispositivo valida. |
| HEAD | Primeros ocho bytes como palabra little-endian de 64 bits. Se conserva el prefijo del dispositivo antes de leer configuracion. |
| PTR / EXP | Puntero del evento y puntero esperado, en los 32 bits bajos del perfil DMA bajo 256 MiB. |

Los valores corresponden a la ultima operacion, no a un historial.
Cada espera borra el evento anterior para no presentar un exito antiguo
como respuesta de una operacion que no termino. Un error se conserva
antes de comprobarlo; no se acepta una respuesta por el hecho de mostrarla.
No se amplian las guardas: sonda 4095/4096 B, puerta 1189/2048 B,
escritorio REPORTES 8057/8192 B RX y SBEF de 11453 B.

QEMU comprueba los digitos del framebuffer contra los eventos y datos
esperados, a velocidad alta y completa. `--xhci-ep0-stall` envia una
peticion no admitida al dispositivo emulado y exige CC 06, fase 23,
parada y revocacion de Bus Master. Ese perfil solo produce `qemu-only/`
y nunca debe instalarse en A:. El perfil normal corregido necesita una
nueva prueba AMD para saber si la publicacion era la causa del bloqueo.
