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
| EP | Estado del endpoint en el contexto de salida visible a CPU. |
| CS | Tamano del contexto descubierto, 20h o 40h bytes. |
| MPS | Max Packet Size configurado en el contexto de salida; no requiere haber recibido el descriptor. |
| OUT / IN | Punteros EP0 de los contextos de salida y entrada, con DCS en bit 0. |
| EXP | Puntero esperado de terminacion, en los 32 bits bajos del perfil DMA bajo 256 MiB. |

La vista anterior mostraba LEFT, REQ, HEAD y PTR. Esos datos permanecen
disponibles mediante los selectores 8..12 del perfil. Esta vista prioriza
el contexto porque las dos fotos AMD siguieron sin evento de EP0. IN y
OUT pueden diferir correctamente cuando avanza el anillo; ademas el xHC
puede mantener informacion en cache. Un OUT que no cambia, por si solo,
no demuestra que el controlador no haya leido la transferencia.

Los valores corresponden a la ultima operacion, no a un historial.
Cada espera borra el evento anterior para no presentar un exito antiguo
como respuesta de una operacion que no termino. Un error se conserva
antes de comprobarlo; no se acepta una respuesta por el hecho de mostrarla.
No se amplian las guardas: la sonda dirigida al puerto 2 ocupa 4091/4096 B;
el escritorio REPORTES ocupa 8073/8192 B RX y su SBEF 11461 B. La puerta
conserva su limite de 2048 B; sus bytes se registran en cada run.

QEMU comprueba los digitos del framebuffer contra los eventos y datos
esperados, a velocidad alta y completa. `--xhci-ep0-stall` envia una
peticion no admitida al dispositivo emulado y exige CC 06, fase 23,
parada y revocacion de Bus Master. Ese perfil solo produce `qemu-only/`
y nunca debe instalarse en A:. El perfil normal corregido necesita una
nueva prueba AMD para saber si la publicacion era la causa del bloqueo.

La siguiente foto AMD mostro P 01, S 01, REQ 0008 y CC/HEAD/PTR en cero:
no se capturo terminacion de transferencia. Comparar con el padre revelo
otra omision: se pedia el descriptor inmediatamente despues de Address
Device. BMO-X espera `PLAZO_ASENTAR_MS` antes de continuar; USB tambien
contempla recuperacion tras SET_ADDRESS. La nueva sonda conserva el
debounce previo y repite el muestreo PIT despues de direccionar, antes
de publicar la primera peticion EP0. Son al menos 110 ms conservadores
en este perfil finito, no una latencia obligatoria para cada lectura
ni una garantia de respuesta del periferico.

QEMU completa las tres fases de estabilizacion en 33 muestras, unos
330 ms totales, y mantiene el limite global de 100 muestras. Un fallo
del temporizador o de estabilidad detiene la prueba antes del descriptor.
Para conservar la pagina RX se escriben campos cortos de Setup/Status
en TRBs nuevos, ya puestos a cero por el asignador UEFI; nunca se
reutilizan esos TRBs. No se quitan validaciones de terminacion ni MPS.
El resultado en AMD de esta espera posterior aun necesita confirmacion.

## Seleccion explicita del puerto

La foto posterior mantuvo P 01, S 01 y ningun evento. El inventario previo
del equipo situaba teclado y raton en los puertos USB 2 y 3 del AMD. Esa
topologia es una referencia; la identidad debe confirmarse leyendo sus
descriptores. `--usb-root-port 2` selecciona exclusivamente ese puerto
raiz PORTSC, comprueba MaxPorts, CCS y la velocidad y no intenta otro
si falla. El perfil automatico sigue disponible al omitir el argumento.

Se corrigio la lectura de MaxPorts en esta sonda: usa el byte del snapshot
HCSPARAMS1 capturado mediante una lectura MMIO de 32 bits. La lectura
anterior de un byte en MMIO +7 devolvio cero en QEMU. Tambien se aislan
los cuatro bits de velocidad antes de compararlos; los demas bits de
PORTSC no forman parte del ID de velocidad.

El ensayo dirigido configura QEMU con `p3=0`: sus puertos raiz USB2 1 y 2
contienen teclado y raton. Esto solo define la topologia de prueba del
emulador; no reconfigura puertos fisicos AMD. QEMU prueba el puerto 2 a
velocidad alta y completa, y rechaza puerto 3 vacio y 255 fuera de rango
sin caer al primero ni acceder fuera del banco admitido.

```powershell
& $reportPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-ab5e8222cf60 --xhci-enum-probe --reports-desktop build/desktop/desktop-reports.sbef --usb-root-port 2 --ram-mib 256
```

La copia instalada para la siguiente prueba fisica usa el puerto 2. Sigue
siendo enumeracion finita sin endpoints HID activos. Si aparece P 02 y
DESCRIPTORES OK, aun faltara configurar las interfaces y recibir informes.
