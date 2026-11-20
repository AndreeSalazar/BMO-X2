# ULTRA-J

## Interfaz elegante con RmlUi

Primera prueba real en HOST: `examples/rmlui-desktop/` separa estructura
RML, apariencia RCSS y accion `main.uj`. RmlUi 6.3 + FreeType dibujan
texto, paneles y boton mediante un adaptador CPU C++ compilado con Clang.
El click programado ejecuta UJBC en el runtime HOST actual y cambia la
vista. HOST empaqueta recursos, DLL, licencias y hashes. Todavia no es
un ejecutable SBEF ni una interfaz instalada en el escritorio de BMO-X2.

[Construccion, evidencia y limites](../tools/desktop/rmlui/README.md).
El motor visual C++ no reemplaza a Rust como director del escritorio;
requiere un puente y servicios adaptados antes de llegar a Ring 3.
El dibujador comun ya vive en Rust no_std y paso una sonda SBEF en CPL3;
la vista HOST lo usa con pixeles identicos al backend C++ inicial.
Esto no implica que RmlUi completo ni su callback Python vivan en el invitado.
El perfil `bmo-ui-memory-v1` ya recibe recursos en memoria y tiempo
inyectado, anima RCSS, procesa puntero y llama a la accion UJBC HOST.
Prueba movimiento reducido, cierre/reentrada y rechazos de recursos,
RCSS y funciones graficas fuera del perfil. `tools/desktop/rmlui/live.py`
genera la demostracion animada real; la evidencia sigue siendo HOST.

## Por que existe

ULTRA-J es el lenguaje de aplicaciones de BMO-X2. Nacio para escribir
objetos y sus eventos con una sintaxis familiar de Java, construirlos
en HOST y ejecutarlos en Ring 3 con permisos de BMO-X2. El objetivo es
dar al autor control sobre la codificacion de las acciones, la memoria
por region y los efectos que cada aplicacion puede solicitar.

Cada instruccion compilada tiene una codificacion UJBC definida por
version. Esa relacion permite inspeccionar los bytes y verificarlos
antes de entregarlos al interprete. Rust sostiene los servicios
nativos del sistema y tambien sirve como referencia de medicion. La
prioridad de ULTRA-J es dar al autor un flujo directo y verificable.

Su primer campo es el escritorio. El mismo modelo esta pensado para utilidades,
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

El compilador visual HOST esta separado en `ui/style.py` (perfil de
estilos .ujc) y `ui/view.py` (estructura .ujh, geometria y emision UJVI).
`view.py` conserva la entrada CLI e importaciones existentes. Las capas
del servicio se describen en [Desktop](../userspace/services/desktop/LAYERS.md).
La [evidencia HOST](evidence/ui-layers-host.json) registra la equivalencia
binaria antes/despues y las pruebas de regresion de esta separacion.

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
en `targets/x86_64/` para organizar y verificar responsabilidades.
La portabilidad entre CPUs no es objetivo ni requisito de BMO-X2.
UJBC organiza la ejecucion dentro de su runtime; SBEF admite el binario
del destino. Una variante para otra CPU seria un proyecto separado con
su propio backend y runtime. El trabajo actual es exclusivo x86-64.

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

## Papel de C, Rust y Java

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
y 64 bytes de contenedor. Reproduce la medicion de construccion con
`python -B .\Ultra-J\compare_build.py` desde la raiz de BMO-X2. Usa
LLVM para enlazar y Rust con el destino `x86_64-unknown-none`.

En una segunda medicion, el compilador residente tardo 0,053 ms de
mediana en compilar y verificar en memoria (1001 corridas).
Con `--watch`, la mediana desde guardar hasta publicar el UJBC bajo
la misma prueba paso de 203,7 ms con sondeo cada 250 ms a 8,9 ms
con sondeo cada 10 ms (11 cambios validos por configuracion).
Un proceso nuevo de ULTRA-J tardo 81,4 ms en esa segunda prueba.
El modo residente revisa el archivo con mayor frecuencia mientras
esta activo. La medicion incluye guardado y reemplazo atomico.

### Huella del interprete en Ring 3

QEMU verifica la vista y UJBC v1/v2. La consola UJBC v3 se ejecuta en HOST.

El panel `examples/panel` produce un `view.sbef` de 4.401 B que
incluye 3.516 B de vista UJVI y 753 B de codigo para el presentador,
la entrada y la VM. Medido entre los simbolos `run_action` e `invalid`,
el interprete ocupa 376 B y comparte una trampa `UD2` de 2 B. Reserva
256 B en `.bss`. La accion externa `ACTION.UJB` mide 23 B y ocupa
48 B de la arena al crear un `Window` de 32 B y un `Button` de 16 B.
QEMU verifica que la arena vuelve a cero al terminar.

En `run-desktop-media-c5cf4aae8961`, QEMU verifico tres paginas del
SBEF mas una para la pila. En `run-desktop-media-35e3c1d85d36`, el
lanzador de escritorio uso cuatro paginas del SBEF mas una para la
pila. Ambos ensayos configuraron 256 MiB de RAM para el invitado.
[Huella del sistema](../docs/FOOTPRINT.md).

Python compila el fuente de ULTRA-J a UJBC, prepara UJVI y empaqueta
el SBEF desde el ELF. Clang ensambla el presentador x86-64 y LLD lo
enlaza. En Ring 3, el presentador nativo ejecuta UJBC sin Python.
GCC y MSVC son productores de codigo nativo opcionales en el flujo
de HOST. El banco `-Benchmark` usa Rust para compilar la referencia.

### Comparacion de ejecucion con Rust

Agrega `-Benchmark` al [comando de arranque directo](#arranque-directo-al-panel).
Requiere `rustc` con el destino `x86_64-unknown-none`. Ambos caminos
crean un Window y un Button, ejecutan los metodos y limpian los 48 B
de objetos en la misma arena. La referencia Rust tiene la accion
compilada de antemano. UJBC lee y verifica las instrucciones al correr.

El ensayo `run-desktop-media-4350986a5eb7` uso QEMU 11.1.0 TCG con
una CPU `qemu64`, 256 MiB asignados y Rust 1.99.1 con `opt-level=2`.
Despues del calentamiento, alterno el
orden de las muestras en 31 lotes de 2.048 acciones por implementacion.
El invitado registra el contador TSC y la sonda comprueba el resultado
y que la arena este limpia. El cronometro abarca la llamada y el bucle
de medida. La presentacion y las llamadas al kernel quedan fuera.

| Implementacion | Mediana TSC por accion | P95 TSC por accion |
|---|---:|---:|
| Interprete UJBC | 832,247 | 867,495 |
| Rust nativo, `no_std` | 98,408 | 114,848 |

Estas unidades pertenecen al reloj emulado de QEMU TCG. Para medir
ciclos fisicos hace falta repetir el ensayo en hardware. El
`qemu-results.json` conserva el plan SBEF. Las muestras y los hashes
del ensayo estan en el [informe versionado](evidence/ring3-execution.json).

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

### Puente de registro de drivers en HOST

`uj.py new driver` crea una carpeta con `main.uj`. El perfil declarativo
`Driver.register` se valida en HOST y referencia un backend nativo SBEF
ABI 1 ya construido. No agrega instrucciones a UJBC ni ejecuta esas
llamadas en la VM actual. El runtime de drivers y las concesiones del
NANO-CORE siguen pendientes.

Desde BMO-X2, con `$ujPython` del ejemplo anterior:

```powershell
$ujCli = (Resolve-Path .\Ultra-J\uj.py).Path
Set-Location .\userspace\drivers
& $ujPython -B $ujCli new driver usb_input --pci 1022:149C
Set-Location .\usb_input
# Colocar aqui el backend real del servicio: backend.sbef.
& $ujPython -B $ujCli driver check
& $ujPython -B $ujCli driver prepare
```

La plantilla requiere el backend: sin ese archivo devuelve un error
con su ruta. No crea carpetas vacias ni un ejecutable de relleno.
El archivo generado usa este perfil:

```java
class UsbInput {
    void register() {
        Driver.target("x86-64");
        Driver.pci("1022:149C");
        Driver.backend("backend.sbef");
        Driver.memory(65536);
        Driver.mmio(0, 0, 65536);
        Driver.dma(40960);
        Driver.events();
    }
}
```

Los valores de memoria y ventanas de la plantilla son solicitudes que
deben ajustarse al backend y dispositivo. `mmio(bar, offset, bytes)`
usa desplazamientos del BAR, sin direcciones fisicas arbitrarias.
`dma(bytes)` solicita paginas con aislamiento IOMMU. `memory(bytes)`
limita la solicitud de memoria CPU; HOST comprueba el suelo de regiones
SBEF mas 4 KiB de pila. No mide el heap futuro ni concede esa memoria.
Los limites en ejecucion necesitan aplicacion efectiva del NANO-CORE.

`Driver.depends("base");` busca otro registro en
`dependencies/base/main.uj`. Cada dependencia tiene su propio backend
local. HOST calcula el orden, conserva hashes de fuentes y binarios,
y rechaza ciclos y rutas fuera del paquete. Son dependencias de
servicios de driver, no un mecanismo de enlace de bibliotecas nativas.
Los errores incluyen archivo y, al analizar declaraciones, linea y
columna. El informe de dependencias usa el mismo mecanismo de SUPER
GRAFO que los otros paquetes de ULTRA-J.

`driver prepare` publica atomicamente `build/driver-request.json`.
Contiene `HostValidated: true`, `RuntimeReady: false` y
`GrantedCapabilities: []`. Es un registro de solicitudes, no un permiso
ni un binario nuevo para el kernel. Verificar el contenedor no prueba
que su codigo implemente un driver funcional. Un fallo posterior
conserva el ultimo registro valido; antes de usarlo deben comprobarse
de nuevo sus hashes y el SBEF actual.

El perfil no admite acceso root, IOPL global, ejecucion de comandos ni
llamadas arbitrarias. Reutilizar este puente evitara modificar Ring 0
para cada registro cuando exista la ruta general de concesiones y
arranque de servicios. Hoy valida y prepara en HOST, sin iniciar el
driver ni hacer funcionar USB en metal.

Comprueba el perfil con `python -B Ultra-J/test_driver.py`.

### Crates de aplicacion

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

## Orden para madurar ULTRA-J

El perfil comprobado carga una accion UJBC desde FAT32 durante el arranque
y la ejecuta en el escritorio. El lanzador actual comparte las paginas
del escritorio. El interprete de la sonda usa una arena de 256 B y recibe
su accion en una direccion fija. La [huella medida](../docs/FOOTPRINT.md)
es la referencia para comparar las entregas siguientes.

| Orden | Entrega | Criterio de cierre |
|---:|---|---|
| 1 | Dos instancias del interprete en Ring 3 | Cada instancia recibe su propio bytecode acotado y su propia arena. Cerrar A limpia su arena y B sigue funcionando. Una accion invalida devuelve un motivo y la ubicacion del error. |
| 2 | Dos ventanas en DIRECTOR | Cada ventana recibe sus propios eventos, conserva su estado al cambiar el foco y libera sus recursos al cerrar. QEMU registra memoria, reapertura y tiempo desde la entrada hasta el cuadro presentado. |
| 3 | Aplicaciones como procesos SBEF | El cargador CASM da a cada proceso su propio espacio de direcciones y capacidades. Se prueba que una salida o un fallo recupera sus paginas y que la otra aplicacion sigue operativa. [Cargador SBEF](../contracts/SBEF-LOADER.md). |
| 4 | Aplicaciones y superficies | Una utilidad de CABINA prueba texto y permisos de archivo. Un juego 2D prueba entrada simultanea, reloj, dibujo por lotes y tiempo por cuadro con resolucion fija. Las aplicaciones multimedia agregan colas y un reloj comun para audio y video. |
| 5 | Emision nativa y autocompilacion | Medir primero las rutas de ejecucion mas costosas. Para autocompilar hacen falta metodos con argumentos, control de flujo y buffers de bytes acotados. La prueba de cierre compara la salida de dos generaciones del compilador. |

### Primera entrega: dos acciones, dos arenas

Pasar al interprete un rango UJBC y una arena explicita. Conservar un
solo interprete y la codificacion v2. El perfil de arranque puede
preparar ambas acciones con HOST antes de incorporar la lectura de
aplicaciones desde la sesion activa.

El recorrido en QEMU debe alternar A y B, verificar que solo cambie la
arena que corresponde a la accion, cerrar A, comprobar su borrado
y volver a ejecutar B. Una accion invalida debe dejar intacto el
estado de la otra instancia y permitir que DIRECTOR conserve el control.
El informe debe registrar bytes de codigo, arena reservada y activa,
paginas de usuario y el diagnostico observado. Esta primera entrega
comprueba la separacion de estado dentro de una sesion de Ring 3. El
aislamiento con permisos de memoria entre procesos corresponde a la
entrega 3.

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
    -DesktopRun build/CASM/run-desktop-3c09ddaa8ea6 `
    -RamMiB 256
```

El ensayo comprueba ambos fotogramas de la intro, los colores de la
vista, la accion con Enter, el reinicio con Esc, el BOOTLOG.TXT de FAT32 y el rechazo
de un SBEF con permisos W+X. Abre el run impreso con
`tools/boot/view.ps1 -Run <ruta-del-run>`. La evidencia es QEMU.
