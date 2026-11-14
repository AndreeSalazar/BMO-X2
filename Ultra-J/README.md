# ULTRA-J

## Por que existe

ULTRA-J es el lenguaje de aplicaciones de BMO-X2. Nacio para escribir
objetos y sus eventos con una sintaxis familiar de Java, construirlos
en HOST y ejecutarlos en Ring 3 con permisos de BMO-X2. Su primer
campo es el escritorio. El mismo modelo esta pensado para utilidades,
paneles de diagnostico, automatizacion, herramientas y juegos. Un motor
grafico podria usarlo para escenas, controles y logica, con el dibujo
intensivo a cargo de un servicio nativo si las mediciones lo justifican.

La aplicacion declara comportamiento en `.uj`, estructura de interfaz
en `.ujh` y apariencia en `.ujc`. HOST transforma esos archivos en
binarios versionados. En el modelo previsto, una VM compartida en Ring 3
cargara distintos `.ujb` sin reconstruir el kernel ni enlazar la VM
para cada cambio. Ring 0 conserva su ABI de capacidades y admite el
ejecutable de la VM mediante SBEF.

## Donde aporta frente a C, Rust y Java

| Lenguaje | Papel en BMO-X2 |
|---|---|
| **C** | Permite portar codigo existente, como DOOM, y escribir rutinas nativas con control de memoria. ULTRA-J aspira a reducir el trabajo repetido de definir objetos de interfaz, cerrar grupos de asignaciones y empaquetar cambios de aplicacion. |
| **Rust** | Sostiene los servicios nativos de Ring 3 y aporta comprobaciones de propiedad durante la compilacion. ULTRA-J propone un contrato de bytecode comun y recursos de interfaz binarios que varias aplicaciones podran compartir a traves de una VM. Ambos modelos admiten regiones de memoria. |
| **Java** | Inspira las clases, interfaces y bytecode portable. La JVM estandar administra automaticamente la memoria de objetos. ULTRA-J define para BMO-X2 regiones cuyo cierre devuelve en bloque el espacio de sus objetos. Su modelo de vistas binarias y capacidades apunta a cubrir las necesidades del escritorio con los servicios propios del sistema. |

Los binarios de ULTRA-J tienen su propio contrato. Ejecutar archivos
`.class` o utilizar bibliotecas Java requeriria una capa adicional.
[Especificacion de la JVM](https://docs.oracle.com/en/java/javase/26/docs/specs/jvms/jvms-2.html)

## Que esta medido

`ObjectDemo.uj` y un equivalente minimo en Rust crean una ventana y
un boton como objetos, llaman a sus metodos y terminan su alcance.
La comparacion de HOST tomo la mediana de 11 ejecuciones en Windows,
con Rust `no_std` optimizado para tamano y destino x86-64.

| Artefacto | Tiempo mediano de construccion | Tamano en archivo |
|---|---:|---:|
| ULTRA-J UJBC | 81,6 ms | 26 B |
| Rust ELF | 164,8 ms | 4576 B |
| Rust SBEF | 254,8 ms | 117 B |

El UJBC requiere un runtime. El SBEF incluye 53 bytes de codigo nativo
y 64 bytes de contenedor. Estos tiempos miden produccion del artefacto.
Para medir el coste de ejecucion y RAM queda pendiente correr ambos en
Ring 3 con la misma entrada y contar tambien las paginas de la VM.
Hoy QEMU verifica el presentador de vistas binarias. El verificador
UJBC, las llamadas a objetos y el Reciclador se prueban en HOST.

Reproduce la medicion con `python -B .\Ultra-J\compare_build.py`
desde la raiz de BMO-X2. Usa LLVM para enlazar y Rust con el destino
`x86_64-unknown-none`. Puedes usar `$ujPython` del ejemplo siguiente.

En una segunda medicion, el compilador residente tardo 0,053 ms de
mediana en compilar y verificar en memoria (1001 corridas).
Con `--watch`, la mediana desde guardar hasta publicar el UJBC bajo
la misma prueba paso de 203,7 ms con sondeo cada 250 ms a 8,9 ms
con sondeo cada 10 ms (11 cambios validos por configuracion).
Un proceso nuevo de ULTRA-J tardo 81,4 ms en esa segunda prueba.
El modo residente revisa el archivo con mayor frecuencia mientras
esta activo. La medicion incluye guardado y reemplazo atomico.

## Compilar y verificar objetos

`compiler.py` compila el [ejemplo de escritura Java](examples/WindowDemo.uj)
a `.ujb`. `runtime.py` verifica y ejecuta en HOST. `examples/` guarda
el tema y el vector manual que define los bytes esperados.
El [contrato](FORMAT.md) especifica las instrucciones y el alcance.
El [ejemplo de objetos](examples/ObjectDemo.uj) usa UJBC v2 para llamar
metodos sobre una ventana y un boton con estado propio. Se puede pasar
ese archivo a `compiler.py` en lugar de `WindowDemo.uj` para ver las
llamadas registradas por el runtime HOST.

Desde la raiz de BMO-X2, en PowerShell:

```powershell
$ujPython = (Get-Command python -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $ujPython) {
    $ujPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
$ujOutput = New-Item -ItemType Directory -Force .\build\ultra-j
$ujWords = (Get-Content .\Ultra-J\examples\graphite.ujt.hex -Raw).Trim() -split '\s+'
[byte[]]$ujBytes = foreach ($ujWord in $ujWords) { [Convert]::ToByte($ujWord, 16) }
[IO.File]::WriteAllBytes((Join-Path $ujOutput.FullName 'graphite.ujt'), $ujBytes)
& $ujPython -B .\Ultra-J\compiler.py .\Ultra-J\examples\WindowDemo.uj .\build\ultra-j\window.ujb
& $ujPython -B .\Ultra-J\runtime.py .\build\ultra-j\window.ujb .\build\ultra-j\graphite.ujt
& $ujPython -B .\Ultra-J\test_ultra_j.py
```

El primer cierre recupera 64 bytes de tres objetos. La segunda region
usa de nuevo el offset cero y recupera 32 bytes al cerrar. El informe
separa ese pico de 64 bytes de los 256 reservados por la arena.
Cambiar el tema solo altera la tabla de apariencia. La sonda HOST
informa los estilos y el ciclo de memoria. La ventana visible en QEMU
requiere la integracion con DIRECTOR.

Agrega `--watch` al comando de `compiler.py` para compilar al guardar.
Consulta el fuente cada 10 ms. Publica el binario verificado mediante un
reemplazo atomico y conserva el ultimo binario valido si hay un error.
Deten el proceso con Ctrl+C.

## Vista en QEMU

`examples/panel.ujh` describe dos pantallas con etiquetas y clases.
`examples/panel.ujc` define posicion, dimensiones y colores.
`view.py` aplana ambos a `panel.ujv`. Su cabecera es `UJVI 01 02`,
seguida de dos listas. Cada lista empieza con un contador `u16`.
Cada rectangulo tiene x, y, ancho y alto como `u16`, y color
`0x00RRGGBB` como `u32`, todos little-endian.

El presentador x86-64 carga las listas de solo lectura desde su SBEF.
En Ring 3 solicita el dibujo mediante INVOKE y espera entrada con WAIT.
Enter alterna LISTO y ACTIVO. El perfil admite coordenadas fijas y texto
A-Z/0-9 con la fuente de CABINA. La integracion con objetos `.ujb`,
eventos por elemento y el compositor DIRECTOR queda pendiente.

## Frontera por arquitectura

| Carpeta o archivo | Responsabilidad |
|---|---|
| `compiler.py` y `runtime.py` | Escritura estilo Java, instrucciones UJBC y regiones de objetos. |
| `view.py` | Estructura y estilos de la vista, con coordenadas logicas y salida UJVI. |
| `targets/x86_64/` | Presentador, instrucciones de CPU y empaquetado para el ABI x86-64 de BMO-X2. |
| `qemu.ps1` | Compila la vista, construye el presentador x86-64 y ejecuta el ensayo. |

UJBC, UJTH y UJVI tienen tamanos, orden de bytes y significado fijos
con independencia de la CPU. La capa x86-64 recibe un archivo UJVI ya
compilado y traduce sus rectangulos a peticiones INVOKE del sistema.
Las variables de entrada y la espera de eventos tambien pertenecen
a esa capa. Un futuro destino RISC-V o ARM64 reutilizara los mismos
vectores y aportara su presentador, ABI y formato de carga nativo.

## Ejecutar el ensayo

Con los tres runs de BMO-X2 ya generados, desde la raiz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Ultra-J\qemu.ps1 `
    -AbiRun build/CASM/run-20261112-174958-944cb997 `
    -SplashRun build/CASM/run-20261112-045636-c461240e `
    -DesktopRun build/CASM/run-desktop-3c09ddaa8ea6
```

El ensayo comprueba ambos fotogramas de la intro, los colores de la
vista, la ida y vuelta con Enter, el BOOTLOG.TXT de FAT32 y el rechazo
de un SBEF con permisos W+X. Abre el run impreso con
`tools/boot/view.ps1 -Run <ruta-del-run>`. La evidencia es QEMU.
