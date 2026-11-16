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
