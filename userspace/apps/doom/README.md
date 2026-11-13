# DOOM en BMO-X2

BMO-X compilo DoomGeneric con su propio compilador C x86-64 y produjo
`doom.bex` en BEF2. Ese paquete devuelve `ELF-HEADER` en `e_ident`
(offset 0) al pasarlo al importador SBEF. El camino de BMO-X2 parte del
codigo C y enlaza un ELF64 estatico con el portal ABI 1.

## Sonda reproducible en Windows PowerShell 5.1

Desde la raiz de BMO-X2, con LLVM y Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-doom-probe.ps1
```

El script busca DoomGeneric en el BMO-X vecino y verifica la huella de
`m_fixed.c` del commit `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`.
Para otro checkout de ese commit, pasa `-DoomSource` con la ruta a la
carpeta interna `doomgeneric` que contiene `m_fixed.c`.
El argumento `-Gcc` admite la ruta de un GCC cuyo destino sea x86-64 ELF.
La prueba nativa y el enlace siguen usando LLVM. La prueba de invitado
se verifico con GCC 15.2.0.

| Salida en `build/doom-probe` | Resultado observado con GCC 15.2.0 para ELF |
|---|---|
| `doom-fixed-host.exe` | Cuatro casos de `FixedMul` y `FixedDiv`, incluida saturacion al dividir por cero. |
| `doom-fixed.elf` | Un `PT_LOAD` RX de 452 bytes en offset `0x1000`. |
| `elf-segments.txt` | Direccion virtual, permisos, alineacion y tamanos del segmento. |
| `doom-fixed.sbef` | 516 bytes. Cabecera y tabla de 64 bytes, seguidas por el mismo contenido RX del ELF. |

El contenido RX queda en la direccion virtual `0x40000000` y ocupa una
pagina mapeada de 4096 bytes. Esa cifra cubre la region del binario.

## Prueba de invitado en QEMU

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion abi
$abi = Get-ChildItem .\build\CASM -Directory -Filter 'run-*' |
    Sort-Object LastWriteTime -Descending |
    Where-Object { (Test-Path (Join-Path $_.FullName 'profile.txt')) -and
        (Get-Content (Join-Path $_.FullName 'profile.txt')) -eq 'ring0-abi-probe-0.1' } |
    Select-Object -First 1
$gcc = (Resolve-Path .\build\tools\gcc-15.2.0\bin\x86_64-elf-gcc.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-doom-probe.ps1 -Gcc $gcc -AbiRun $abi.FullName
```

Usa la ruta real de GCC si esta en otra carpeta. El ensayo crea una copia
del perfil ABI verificado y ajusta cinco campos de su vector para admitir
el SBEF de una sola region RX y comprobar su terminal. El paquete de
arranque incorpora el SBEF byte por byte. El monitor coteja el cuerpo
arrancado, tres entradas SYSCALL y el marco de CPL3. La marca final exige
que las cuatro operaciones de DoomGeneric, ECHO, el rechazo de capacidad
y el estado de WAIT hayan pasado. El kernel borra 8192 bytes de usuario.
El run conserva el SBEF, el disco virtual, la captura y el JSON.

El cargador general de SBEF externo y el motor jugable siguen pendientes.

### Intro y Ring 3 en el mismo arranque

Genera un run con `bmo-x2.ps1 -Accion gato-hd` y agrega
`-IntroRun <ruta-del-run-gato-hd>` al comando anterior. El ensayo
verifica los tres cuadros del gato y la ejecucion del SBEF en la
misma VM. El perfil HD y el perfil ABI de referencia conservan sus
vectores. La copia combinada termina en la parada del ensayo.

Para repetir en pantalla el ultimo arranque aprobado con intro:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile doom-intro -Wait
```

El visor espera el titulo de la ventana SDL, intenta darle foco y
publica la ruta del registro serie del invitado. `-Wait` devuelve la
terminal al cerrar QEMU. Para elegir un ensayo exacto, sustituye
`-Profile doom-intro` por `-Run <ruta-del-run-doom>`.
El perfil usa TCG, VGA emulada y SDL con OpenGL desactivado.

Para recompilar toda la secuencia y abrir el resultado en PowerShell 5.1:

```powershell
Set-Location 'C:\Users\Salazar\Documents\BMO-X2'
$ps51 = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$gcc = (Resolve-Path .\build\tools\gcc-15.2.0\bin\x86_64-elf-gcc.exe).Path

& $ps51 -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion gato-hd
if ($LASTEXITCODE) { throw 'Fallo el gato HD' }
& $ps51 -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion abi
if ($LASTEXITCODE) { throw 'Fallo el perfil ABI' }

function Find-BootRun([string]$Profile) {
    Get-ChildItem .\build\CASM -Directory -Filter 'run-*' |
        Sort-Object LastWriteTime -Descending |
        Where-Object {
            $path = Join-Path $_.FullName 'profile.txt'
            (Test-Path -LiteralPath $path) -and (Get-Content -LiteralPath $path) -eq $Profile
        } | Select-Object -First 1 -ExpandProperty FullName
}
$intro = Find-BootRun 'ring0-splash-hd-0.1'
$abi = Find-BootRun 'ring0-abi-probe-0.1'
& $ps51 -NoProfile -ExecutionPolicy Bypass -File .\tools\build-doom-probe.ps1 -Gcc $gcc -AbiRun $abi -IntroRun $intro
if ($LASTEXITCODE) { throw 'Fallo la sonda DOOM' }
& $ps51 -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile doom-intro -Wait
```

## Del escritorio al primer cuadro de DOOM

1. **Cargador CASM.** Recibir un SBEF como archivo independiente del
   paquete de arranque. Validar y mapear varias regiones RX, R y RW/NX,
   inicializar BSS y pila, entrar a CPL3 y recuperar los marcos al salir.
   Probar una imagen Rust y rechazos de tamanos y permisos.
2. **Pantalla y teclado.** Ring 0 concede presentacion e input.
   Ring 3 compone sobre un buffer en RAM y presenta por el framebuffer
   lineal. La prueba cambia de espacio con Ctrl + Super + numero y
   verifica que la ventana enfocada recibe teclas.
3. **Runtime del juego.** Portar las funciones DoomGeneric a las
   capacidades de pantalla, teclado y reloj monotono. Dar al motor
   memoria de trabajo, libc minima y acceso de lectura a un WAD.
4. **Partida en QEMU.** Compilar el motor completo en C con GCC,
   empaquetarlo como SBEF y verificar el primer mapa y una tecla que
   cambie un cuadro. DOOM rasteriza en CPU. Medir el tiempo por cuadro
   y la memoria del proceso antes de ajustar la composicion.
5. **Audio.** Conectar efectos y musica a fuentes independientes del
   [servicio de audio](../../services/audio/AUDIO.md).

[Fuente DoomGeneric fijada](https://github.com/ozkl/doomgeneric/tree/dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284) |
[Cargador SBEF](../../../contracts/SBEF-LOADER.md) |
[Escritorio](../../services/desktop/WORKSPACES.md)

## Ruta directa sin Director

### Prueba GCC con tres regiones SBEF

Agrega `-External` al comando de la sonda con `-Gcc` y `-AbiRun`.
GCC compila el codigo C del invitado y LLD enlaza un ELF64 estatico.
El empaquetador HOST genera `build/doom-probe/doom-external.sbef`
de 656 bytes. QEMU entrega el modulo separado en RAM. La CPU ejecuta
la aritmetica original en CPL3, lee las constantes y modifica datos
y BSS. INVOKE rechaza el dibujo con la capacidad de entrada y
acepta la misma operacion con la capacidad de pantalla. La prueba
coteja los 15360 pixeles del rectangulo verde. El motor completo,
el WAD y la lectura desde disco quedan pendientes.

### Entregas pendientes

| Orden | Entrega | Prueba de cierre |
|---|---|---|
| 1 | Ring 0 CASM carga SBEF independiente del paquete de arranque. | El mismo kernel ejecuta dos SBEF distintos con regiones RX, R y RW/NX, pila, BSS a cero y salida ordenada. |
| 2 | Ring 0 concede presentacion por bloques, entrada enfocada, reloj monotono y lectura de un archivo. | Un cliente CPL3 presenta un cuadro por CPU, recibe teclas y deltas del raton, y lee bytes de un WAD. |
| 3 | El adaptador C implementa `DG_Init`, `DG_DrawFrame`, `DG_GetKey`, `DG_GetTicksMs`, `DG_SleepMs` y `DG_SetWindowTitle`, con libc minima y arena de memoria en Ring 3. | GCC enlaza el motor completo en ELF64 estatico y HOST admite el SBEF. |
| 4 | El lanzador inicia DOOM con una superficie propia y `doom1.wad` como datos. | QEMU alcanza E1M1 y comprueba un cuadro que cambia al enviar una tecla. |
| 5 | La sesion Rust integra foco, captura relativa del puntero, configuracion y audio. | La ventana pierde y recupera la captura sin teclas ni botones pegados. Efectos y musica tienen volumen independiente. |

El WAD local de BMO-externo queda separado del ejecutable. El raton de
escritorio usa coordenadas para foco. El juego necesita deltas relativos
y botones mientras tenga la captura. El adaptador del padre descartaba
estos eventos en `DG_GetKey`; el port debe conectarlos al motor.

El puente actual limita el paquete de arranque a 4096 bytes. El cargador
de la etapa 1 desacopla ese presupuesto del codigo del juego. Antes de
congelar el ABI, cotejar las restricciones del importador HOST (1 MiB
de archivo y ventana virtual de 16 MiB) con el ELF del motor y su arena.

El ensayo externo admite codigo RX de hasta dos paginas, una pagina
de constantes R/NX y una de datos RW/NX con BSS a cero. QEMU
deposita el modulo en RAM y verifica que Ring 3 modifica datos y BSS.
Cuando la tercera region recibe W+X, Ring 0 registra el offset 116
y QEMU verifica que el espacio de usuario
queda sin activar. CABINA ya lista los contadores de WAIT. Mostrar
los rechazos de carga dentro de una sesion requiere conservar el
diagnostico de cada proceso y devolver el control al supervisor.
