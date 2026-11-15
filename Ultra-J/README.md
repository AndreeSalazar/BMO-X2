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

## Vision integrada y limites

El objetivo es un conjunto coherente para aplicaciones: objetos y
eventos en `.uj`, estructura declarativa en `.ujh`, apariencia en `.ujc`
y construccion verificable en HOST. Se busca ampliar progresivamente
el lenguaje y sus bibliotecas para cubrir mas usos. La escritura
familiar de Java no implica ejecutar cualquier programa Java, sus
archivos `.class` ni todas sus bibliotecas. Los perfiles actuales de
markup y estilos tampoco equivalen a HTML/CSS completos ni a un navegador.

HOST analiza texto, resuelve dependencias y transforma las entradas en
UJBC, recursos de vista y, cuando corresponde, un ejecutable SBEF.
El frontend actual esta implementado en Python. Los formatos binarios
no eliminan el analisis sintactico, la comprobacion de tipos ni la
necesidad de construir el programa. Una VM compartida puede reducir
reconstrucciones y duplicacion; falta medir el coste total de esa VM,
los objetos, los recursos y las aplicaciones para demostrar el ahorro.

La semantica y los formatos se mantienen separados del destino nativo
en `targets/x86_64/`. Un UJBC portable necesita una implementacion del
runtime para cada destino; un SBEF con instrucciones x86-64 sigue
siendo x86-64. HOST no es un traductor universal entre CPUs. Solo se
implementa el destino x86-64 en BMO-X2 por ahora.

La CPU ejecuta la aplicacion o su VM en Ring 3. Ring 0 admite el
ejecutable, limita sus capacidades y atiende operaciones privilegiadas.
No interpreta Java, HTML o CSS ni procesa cada instruccion del programa.
La VM y el presentador son los consumidores de UJBC y recursos de vista.

Para madurar este conjunto quedan bibliotecas de objetos y eventos,
modelo de tipos y errores mas amplio, texto y fuentes, layout,
recursos de imagen, accesibilidad, ciclo de vida de las vistas y
gestion de memoria con limites y diagnosticos. Una interfaz completa
necesita ademas entrada HID, compositor y servicios del sistema.
Cada ampliacion debe declarar version de formato, pruebas y costes.
Autohospedaje, compatibilidad Java amplia y optimizacion nativa general
son objetivos posibles que todavia no estan implementados.

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
QEMU verifica la vista y el interprete UJBC v1/v2 de Ring 3.
El perfil de consola UJBC v3 se ejecuta en HOST.

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

## La carpeta es el manifiesto

Para comenzar un crate de consola, ejecuta estos comandos desde el
directorio que alojara la carpeta. En la raiz de BMO-X2 puedes usar:

```powershell
$ujCli = (Resolve-Path .\Ultra-J\uj.py).Path
& $ujPython -B $ujCli new crate hola
Set-Location .\hola
& $ujPython -B $ujCli run
```

`new crate hola` crea `hola/main.uj` con
`Console.println("Hola mundo");`. `run` y `Run` usan la carpeta actual,
compilan su entrada y publican `build/main.ujb` dentro del crate.
El programa se ejecuta en HOST. Los crates que llama pueden vivir en
`crates/<Nombre>/main.uj` debajo de la misma carpeta. Si el crate creado
esta en BMO-X2, SUPER GRAFO puede leer su informe de dependencias.
Para vistas, el constructor del perfil de panel conserva las entradas
que se explican a continuacion.

El nombre de la carpeta identifica el paquete. Sus subcarpetas declaran
las entradas y dependencias. Esta es la estructura usada por el panel:

```text
panel/
  action/main.uj
  crates/Activate/main.uj
  view/main.ujh
  dependencies/graphite/1/style.ujc
```

`action/main.uj` contiene el comportamiento y `view/main.ujh` la vista.
Los estilos del propio paquete pueden ir en `view/style.ujc`. Cada
dependencia local contiene una carpeta de version y su `style.ujc`.
HOST resuelve el grafo por rutas y rechaza clases de estilo duplicadas
o versiones ambiguas. Este primer perfil admite dependencias de estilo.

El `main.uj` del escenario llama a `Activate.run(1);`. HOST lo conecta
con `crates/Activate/main.uj`, cuya clase `Activate` declara
`static void run(int id)`. El parametro toma un ID entero de 1 a 255.
HOST lo resuelve al construir el escenario. Un crate puede usarlo al
abrir su region o pasarlo a otro crate. Tambien existe la firma sin
parametros `static void run()`. Una llamada comienza fuera de cualquier region
abierta y el crate libera sus regiones antes de retornar. HOST incorpora
las instrucciones de cada crate invocado en el orden de llamada. Las
carpetas de crates que el escenario deja sin usar quedan fuera del UJBC.
El informe muestra el enlace, la llamada y su linea. Los ciclos y las
entradas ausentes se diagnostican antes de publicar el binario.
Si la firma no coincide, el informe apunta a la declaracion y registra
la linea y la columna de la llamada.

Ring 3 ya recibe el `.ujb` del escenario como archivo separado en el
perfil de arranque QEMU. Ahora toca cargar aplicaciones desde la
sesion activa, conectar los eventos de cada ventana con DIRECTOR y
ejercitar dos aplicaciones con regiones independientes en QEMU.

Desde la raiz, `& $ujPython -B .\Ultra-J\package.py .\Ultra-J\examples\panel .\build\ultra-j`
genera UJBC y UJVI y muestra las conexiones en JSON. Si falta
`dependencies/graphite/1/style.ujc`, indica que lo requiere
`view/main.ujh`. Los errores de sintaxis de la accion incluyen archivo,
linea, columna y frase esperada.

### Ver el paquete en SUPER GRAFO

Compila el paquete, abre BMO-X2 con `bmo-x2.ps1 -Accion abrir` y
selecciona `Ultra-J/examples/panel` en el Explorador o en el Grafo.
El panel **ULTRA-J · Dependencias** del Explorador muestra las
conexiones del ultimo intento de compilacion, incluso si fallo.
Puedes abrir los archivos desde la lista y saltar a la linea del error.
Para un archivo ausente, el enlace lleva a su carpeta si existe.
Al volver a compilar con exito se actualiza el informe y desaparece el
error. Los informes viven bajo `build/ultra-j/graph/`.

Si SUPER GRAFO es de una revision anterior, reconstruyelo con
`bmo-x2.ps1 -Accion preparar-grafo`.

## Vista en QEMU

`examples/panel/view/main.ujh` describe dos pantallas con etiquetas y clases.
El estilo Graphite define posicion, dimensiones y colores.
`view.py` aplana ambos a `panel.ujv`. La version 2 empieza con
`UJVI 02 02`, un contador `u16` de colores y hasta 64 colores RGB
como `u32`. Siguen dos listas con un contador `u16` cada una.
En cada rectangulo de 6 bytes, los campos x, y, ancho, alto e indice
de color ocupan 10, 9, 10, 9 y 6 bits desde el bit menos significativo.
Los 4 bits superiores quedan a cero. Todos los valores son little-endian.
El presentador incluido lee esta version del formato.

El tema admite esquinas redondeadas, escala entera de texto y centrado.
HOST convierte esos estilos a rectangulos antes de arrancar QEMU.

El presentador x86-64 carga las listas de solo lectura desde su SBEF.
En Ring 3 solicita el dibujo mediante INVOKE y espera entrada con WAIT.
Enter ejecuta la accion compilada de [main.uj](examples/panel/action/main.uj).
El interprete recorre UJBC v1/v2 y comprueba rangos, regiones y metodos
durante la ejecucion. El ejemplo crea Window y Button, ejecuta `show()`
y `activate()`, copia el resultado por valor y borra la memoria al
cerrar la region. QEMU coteja los 256 bytes de la arena al terminar.
El resultado cambia LISTO por ACTIVO. Esc devuelve el panel a LISTO.
El perfil de vista admite coordenadas fijas y texto
A-Z/0-9 con la fuente de CABINA. El SBEF incorpora la vista. UEFI lee
la accion de `BMO-X2/ACTION.UJB` en FAT32 antes de ExitBootServices.
El cargador copia la longitud y el contenido a `0x40003df8`, en una
pagina de solo lectura y sin ejecucion. La accion admite de 9 a 512
bytes y puede cambiarse conservando el mismo SBEF.

BMO-X2 conserva en Ring 0 las capacidades y el acceso a los dispositivos.
ULTRA-J toma la logica de aplicacion, estructura y estilos en Ring 3.
Los servicios nativos, las bibliotecas portadas y las rutas criticas
medidas pueden usar Rust o C. Para usar ULTRA-J en el escritorio habitual
faltan la carga desde la sesion activa, su conexion con DIRECTOR y dos
ventanas con eventos y cierre independientes. La entrada USB en metal
se verifica por separado. [Primer BOOT](../docs/FIRST-BOOT.md)

## Que falta para aplicaciones completas

| Uso | Siguiente base y prueba |
|---|---|
| Aplicaciones de escritorio | VM de Ring 3 que cargue UJBC separado, metodos y campos de usuario, y eventos por elemento en DIRECTOR. Probar dos ventanas aisladas y recuperar la region al cerrar una. |
| Autocompilacion | Metodos con argumentos, control de flujo y buffers de bytes acotados. Compilar el compilador escrito en ULTRA-J y comprobar dos generaciones identicas. |
| Juegos | Superficies y dibujo por lotes, teclado y raton simultaneos, temporizador, audio y activos. Empezar con un juego 2D y medir tiempo por cuadro, latencia de entrada y RAM. |
| Contenido y video | Lectura secuencial de archivos, colas de audio y video y reloj comun. Empezar con una secuencia corta de cuadros y PCM. Para MP4 hacen falta un lector del contenedor y decodificadores para los codecs elegidos. [Registro de codecs MP4](https://mp4ra.org/registered-types/codecs) |

El objetivo de escritura 1:1 es que cada construccion admitida tenga
una traduccion binaria definida. Los espacios, comentarios y nombres
resueltos pueden compartir la misma salida. La compatibilidad con Java
se limita al subconjunto documentado. Comparar con Rust, C o C++ en
juegos y video requiere medir el mismo contenido y el mismo trabajo,
incluyendo la VM y los servicios de audio y video.

## Frontera por arquitectura

| Carpeta o archivo | Responsabilidad |
|---|---|
| `compiler.py` y `runtime.py` | Escritura estilo Java, instrucciones UJBC y regiones de objetos. |
| `view.py` | Estructura y estilos de la vista, con coordenadas logicas y salida UJVI. |
| `targets/x86_64/guest_view.S` | Presentador del panel y llamadas de pantalla y teclado. |
| `targets/x86_64/action_vm.inc` | Interprete UJBC v1/v2, regiones y metodos. |
| `targets/x86_64/build.ps1` | Enlace del presentador y empaquetado SBEF. |
| `qemu.ps1` | Compila la vista, construye el presentador x86-64 y ejecuta el ensayo. |

UJBC, UJTH y UJVI tienen tamanos, orden de bytes y significado fijos
con independencia de la CPU. La capa x86-64 recibe un archivo UJVI ya
compilado y traduce sus rectangulos a peticiones INVOKE del sistema.
Las variables de entrada y la espera de eventos tambien pertenecen
a esa capa. Un futuro destino RISC-V o ARM64 reutilizara los mismos
vectores y aportara su presentador, ABI y formato de carga nativo.

## Ejecutar el ensayo

### Desde el icono del escritorio

El perfil `-Sheet -UltraJ` muestra un icono azul arriba a la izquierda.
El doble clic dibuja la vista de `examples/desktop-panel`. Enter
ejecuta la accion de `ACTION.UJB` y cambia la linea azul a verde.
Super + Q o Esc devuelven el control al mismo espacio de trabajo. La
vista usa el mismo
presentador y el mismo interprete que el panel de arranque.

En PowerShell desde la raiz de BMO-X2, usando `$ujPython` de arriba:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1 -Session -External -Sheet -UltraJ -AbiRun build/CASM/run-20261112-174958-944cb997
& $ujPython -B tools/boot/stage_desktop_media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e build/CASM/run-desktop-3c09ddaa8ea6 --ultra-j-view build/desktop/desktop-ultra-j.sbef --ultra-j-action build/ultra-j/desktop/panel-action.ujb --ultra-j-launcher
```

Abre el run impreso con `tools/boot/view.ps1 -Run <ruta-del-run>`.
El lanzador es un perfil QEMU con raton PS/2 emulado. La vista se
presenta dentro de la sesion actual y toma la pantalla hasta Esc.
Para caber en las dos paginas de texto usa una vista compacta, con
velocidad fija del puntero. El panel de configuracion queda en el
perfil de escritorio habitual.

El mismo recorrido paso con `--ram-mib 256`. El informe de
[huella de BMO-X2](../docs/FOOTPRINT.md) registra artefactos, paginas
y framebuffer, junto con referencias de otros escritorios.

La prueba usa el raton y teclado PS/2 emulados de QEMU. La entrada
USB del AMD 1022:149C y el arranque de este perfil en el equipo siguen
pendientes. [Condiciones del BOOT fisico](../docs/FIRST-BOOT.md)

### Arranque directo al panel

Con los tres runs de BMO-X2 ya generados, desde la raiz:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Ultra-J\qemu.ps1 `
    -AbiRun build/CASM/run-20261112-174958-944cb997 `
    -SplashRun build/CASM/run-20261112-045636-c461240e `
    -DesktopRun build/CASM/run-desktop-3c09ddaa8ea6
```

El ensayo comprueba ambos fotogramas de la intro, los colores de la
vista, la accion con Enter, el reinicio con Esc, el BOOTLOG.TXT de FAT32 y el rechazo
de un SBEF con permisos W+X. Abre el run impreso con
`tools/boot/view.ps1 -Run <ruta-del-run>`. La evidencia es QEMU.
