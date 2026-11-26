# BMO-X2

**Un sistema x86-64 que permite seguir el camino desde el codigo fuente
hasta los bytes que ejecuta la CPU.** CASM construye los perfiles probados
del NANO-CORE en Ring 0. HOST prepara los binarios, SBEF describe como
cargarlos y Ring 3 aloja los servicios, el escritorio y ULTRA-J.

*Eddi Salazar · Lima, Peru*

[Herencia](#herencia-de-tres-proyectos) ·
[HOST](#estado-de-host-y-toolchains) ·
[Arquitectura](#identidad-nano-core-host-aislado-y-ring-3-abierto) ·
[ULTRA-J](#ultra-j-control-desde-la-aplicacion) ·
[Probar en QEMU](#probar-en-qemu)

## Herencia de tres proyectos

BMO-X2 es hijo de BMO-X. Reune tres lineas de trabajo del mismo autor
y elige de cada una las piezas que sirven a su propio diseno.

| Proyecto de origen | Que aporta a BMO-X2 |
|---|---|
| [TALK-CPU x86-64](https://github.com/AndreeSalazar/TALK-CPU-x86-64) | El puente UEFI provisional y la entrega inicial a la CPU. Sus etapas Faggin guian el arranque y sus diagnosticos orientan las pruebas en QEMU y metal. |
| [BMO-X](https://github.com/AndreeSalazar/BMO-X-x86-64) | El modelo de capacidades, aislamiento y diagnostico, junto con INVOKE y WAIT como referencia para el ABI. Sus crates Rust se revisan pieza por pieza para Ring 3. |
| [ULTRA-LinuX](https://github.com/AndreeSalazar/ULTRA-LinuX) | El punto de partida del taller CASM y la inspiracion para espacios de trabajo, foco y atajos del escritorio. |

El puente y el taller CASM tienen procedencia registrada. El kernel
de BMO-X2 se desarrolla con contratos propios y cada pieza adaptada
se comprueba contra ellos. [Procedencia](heritage/README.md) ·
[Inventario de Ring 3](heritage/RING3-TRANSFER.md).

## Estado de HOST y toolchains

**Prioridad actual.** Ampliar HOST y el cargador SBEF externo. La CLI de
HOST se implementa en Python. Los compiladores y enlazadores producen
PE32+ o ELF64. HOST inspecciona el resultado y empaqueta los casos
admitidos en SBEF, con codigo nativo x86-64, permisos y requisitos de
ejecucion. El cargador aplica el contrato y Ring 3 ofrece los servicios
del ABI. El escritorio original arranca por GOP y el ensayo RTX queda
en pausa.

| Productor y perfil | Estado comprobado | Limite actual |
|---|---|---|
| MSVC `cl.exe` + `link.exe`, PE32+ | Cliente C freestanding: PE -> HOST -> SBEF -> CPL3 en QEMU. | No es C++ general, Win32, DLL ni DirectX. El manifiesto ligado al hash no atesta el toolchain. |
| LLVM Clang + LLD, ELF64 estatico | Cliente C freestanding: ELF -> HOST -> SBEF -> CPL3 en QEMU. | La prueba cubre el cliente ABI embebido. |
| LLVM `clang-cl` + `lld-link`, PE32+ | Cliente C freestanding: PE -> HOST -> SBEF -> CPL3 en QEMU. | Perfil PE fijo de una region RX, sin imports. |
| GCC, ELF64 estatico | Cliente ABI en Ring 3 y ruta concreta de DOOM en QEMU. | El cliente ABI se reempaqueto desde el ELF archivado. |
| `rustc`, ELF64 estatico | Cliente ABI en Ring 3 bajo QEMU. Rust sostiene servicios y escritorio. | Cada crate externo necesita cumplir el perfil y sus dependencias. |

La prueba MSVC mas reciente empaqueto un PE de 1,536 bytes como SBEF de
792 bytes y paso en QEMU 11.1.0: ejecucion CPL3, tres llamadas ABI,
rechazo de capacidad invalida, WAIT y recuperacion/limpieza tras fallo.
Es una prueba de un cliente C freestanding, no una prueba de Windows completo
ni de un cargador generico. [Informe QEMU](Reports/host-msvc-qemu.json) |
[Matriz detallada y limites](tools/host/README.md).

`tools/sbef.py pack` y `probe` aceptan `--producer msvc`, `clang-cl`,
`clang`, `gcc` o `rustc`. El selector coteja el formato y reporta el
SHA-256 de entrada. Las cinco rutas tienen una prueba del cliente ABI en
[QEMU](Reports/host-producers-qemu.json).

```powershell
python -B tools/sbef.py profiles
python -B tools/sbef.py probe app.exe --producer msvc
python -B tools/sbef.py pack app.elf app.sbef --producer clang --abi 1
python -B tools/sbef.py plan app.sbef
```

## Principio: compilador primero, destino explicito

La regla de diseno de BMO-X2 es automatizar el trabajo con compiladores y
HOSTs por destino. La frase del proyecto "compilador, no portabilidad" resume
la interpretacion del autor, no es una cita literal de Grace Hopper. La
inspiracion es el trabajo de Hopper en compiladores: A-0 traducia codigo
matematico a instrucciones legibles por la maquina, y FLOW-MATIC acerco la
programacion a terminos de negocio. [Biografia de Yale](https://president.yale.edu/biography-grace-murray-hopper),
[historia del Computer History Museum](https://www.computerhistory.org/timeline/software-languages/).

El objetivo no es meter todos los compiladores dentro de Ring 0. Ring 0
recibe un paquete nativo, con ISA y ABI declarados, y aplica sus reglas de
memoria y capacidades. El HOST ejecuta antes del arranque el trabajo de
adaptar productores, validar semantica, optimizar y emitir el paquete. Es una
herramienta del entorno de desarrollo: el kernel no necesita compilar ni
llevar dentro MSVC, LLVM, GCC o `rustc`. No se busca un ejecutable universal;
cada destino recibe un paquete nativo propio.

| Etapa | Objetivo simple | Estado y salida |
|---|---|---|
| Productor | Producir codigo desde C/C++, Rust, ULTRA-J u otro lenguaje. | MSVC, LLVM/Clang, GCC y `rustc` tienen rutas de prueba limitadas; el nombre no implica admision general. |
| Adaptador | Entender el formato/version de un productor y extraer lo que el HOST sabe interpretar. | Hoy hay importacion acotada de ELF64/PE x86-64. Adaptadores de productores a IR BMO estan pendientes. |
| IR BMO | Guardar operaciones y reglas del programa sin fijarlas a registros/instrucciones x86. | Diseno acordado; semantica y codificacion binaria pendientes. Lo desconocido debe diagnosticarse. |
| HOST | Validar, informar, optimizar de forma semantica y elegir el perfil del destino. | Ya hace admision/empaquetado acotados para x86-64; normalizacion/optimizacion general sobre IR aun pendiente. |
| Backend | Traducir IR a instrucciones, registros, ABI y relocaciones de una ISA. | La ruta actual empaqueta codigo x86 ya generado. Backend IR-BMO a x86-64 pendiente; POWER/Cell requieren backends separados. |
| Paquete | Describir codigo, regiones, permisos, arquitectura, ABI y requisitos. | BMO-X2 usa SBEF x86-64. Cada arquitectura futura necesita un contrato de paquete propio. |
| NANO-CORE | Verificar el paquete, preparar memoria/capacidades y entrar a Ring 3. | Kernel CASM exclusivo x86-64; la comprobacion general de perfil ISA en CASM y el cargador externo siguen parciales. No interpreta C, Rust ni LLVM. |
| Runtime Ring 3 | Dar al programa sus servicios, bibliotecas y ABI de usuario. | Hay servicios y fixtures concretos; runtimes generales de MSVC, Linux o cualquier lenguaje siguen pendientes. |

```text
Ruta actual comprobada:
GCC -> ELF64 x86-64 -> HOST/importador x86 -> SBEF x86-64 -> NANO-CORE x86 -> Ring 3

Ruta futura desde IR BMO:
productores -> adaptadores -> IR BMO binaria -> HOST valida/optimiza
                                            +-> backend x86-64 -> SBEF x86-64 -> NANO-CORE x86
                                            +-> backend POWER  -> paquete POWER -> NANO-CORE POWER
                                            +-> backend Cell   -> paquete Cell  -> NANO-CORE Cell
```

La ruta actual recibe codigo maquina x86-64 y el HOST lo admite/empaqueta
segun sus reglas. Para emitir otra ISA, el adaptador debe entregar fuente o
IR antes de la generacion de instrucciones x86. Un ELF/PE nativo ya enlazado
no cambia de ISA al reescribir su encabezado: moverlo a otro destino
requeriria un traductor binario aparte. Si el juego usa ABI, runtime,
graficos, audio o entrada especificos, el destino tambien debe ofrecer esos
servicios. Su logica y recursos pueden permanecer iguales cuando la IR y
esos contratos preserven el comportamiento requerido.

La IR comun solo contendra operaciones cuya semantica el HOST pueda
representar y validar. Una operacion especifica de una ISA se traduce si
existe una regla definida; si no, el HOST emite un diagnostico. El alcance
actual de BMO-X2 y SBEF sigue siendo exclusivamente x86-64. El contrato de
diseno esta en [IR BMO](contracts/IR-BMO.md); no declara admision de todos los
toolchains.

### Que falta para ampliar la admision

1. **Cargador externo:** trasladar el validador provisional a CASM; admitir
   regiones SBEF segun el contrato, preparar pila/BSS, entrar a CPL3 y recuperar
   todas las paginas en salida o fallo. HOST y CASM deben coincidir en mapa y
   rechazos bajo QEMU.
2. **Perfil x86-64:** la base `x86-64-v1` ya esta fijada y SBEF v2 declara
   perfiles v1-v4; falta llevar el chequeo CPUID/XCR0 de las sondas LLVM al
   cargador CASM general despues de cerrar la puerta 1.
3. **Fixtures por productor:** cerrar muestras freestanding sin imports para
   MSVC, Clang/LLD, clang-cl/lld-link, GCC y Rust. Registrar automaticamente
   versiones, opciones y hashes; cada pareja de productor/enlazador necesita
   evidencia propia, aunque comparta un lector ELF o PE.
4. **Puentes ABI:** definir el ABI BMO-X2 y probar los puentes Microsoft x64,
   SysV y `extern "C"` en sus bordes. No asumir que un lenguaje garantiza
   compatibilidad binaria con otro.
5. **Runtimes e imports:** incorporar servicios versionados por perfil para
   inicio, memoria, libc/CRT, TLS, excepciones/`unwind`, RTTI y bibliotecas.
   Todo import o requisito no soportado debe producir un rechazo identificable.

La secuencia y sus criterios viven tambien en la salida estructurada de
`python -B tools/sbef.py profiles`. Se puede preparar trabajo de puertas
posteriores, pero no declarar soporte general hasta cerrar las anteriores.

La sonda externa de escritorio ya confronta el mapa generado por HOST
con las paginas de un SBEF v2 cargado desde FAT32 en QEMU. `qemu64` admite
el perfil v1, rechaza el requisito v3 y detiene dos paquetes con campos
invalidos antes de copiar codigo. El resultado corresponde a la sonda
LLVM de tres regiones. [Evidencia de carga externa](Reports/host-external-sbef-isa-qemu.json).

El validador estructural escrito en CASM Native comprueba hasta ocho
regiones y coincide con HOST en 29 casos. La sonda freestanding de QEMU
lo invoca en Ring 0 despues de ExitBootServices. El perfil externo de
QEMU lee un SBEF de ocho regiones desde FAT32, lo admite con CASM y entra
en Ring 3. El cierre normal y el fallo de escritura convergen en el mismo
borrado y restauracion de mapa. El cliente llama a INVOKE y WAIT mediante
SYSCALL. WAIT duerme hasta un plazo monotono. Un ensayo con dos espacios
de direcciones verifica que una senal del segundo contexto reanuda al
cliente antes del plazo. La sonda recupera tambien una pila de retorno
invalida. Quedan pendientes el planificador y los servicios de proceso.
[Contrato y evidencia de admision](contracts/SBEF-LOADER.md).

El mismo cargador de prueba ejecuta desde FAT32 el SBEF v2 que HOST
empaqueto de un PE MSVC con cuatro regiones. En CPL3, el binario usa su
puntero reubicado `DIR64` para actualizar datos. La prueba de control
detecta un fallo al devolver el puntero a la direccion original.
[Evidencia MSVC en QEMU](Reports/host-msvc-rebase-qemu.json).

La consola `win64-console-v1` carga un SBEF externo de MSVC en su propio
espacio de Ring 3. HOST resuelve tres imports de KERNEL32 usando el
runtime Rust. El cliente lee el reloj, espera, escribe en stdout y sale
por SYSCALL. El perfil tiene evidencia QEMU para este cliente.
[Informe de la consola](Reports/host-msvc-console-qemu.json).

## Escritorio, entrada y arranque

El nuevo candidato de escritorio conecta RmlUi con DIRECTOR Rust:
Ctrl+Super+1..4 cambia espacios, Super+Q cierra el panel y F1 lo reabre.
Arranca desde archivos FAT32 reales en QEMU y dispone de un EFI separado
para prueba fisica. El 16-11-2026 el propietario confirmo el escritorio
en METAL AMD a 1920x1080 con fotografia y BOOTLOG; despues confirmo que
teclado y raton USB respondian en el escritorio.
[Evidencia METAL](Reports/rmlui-desktop-metal-20261116.json).
[Ruta de arranque, controles y limites](docs/NATIVE-DESKTOP-BOOT.md).

**BMO-X2 (Original)** usa `DESKTOP.EFI`, RmlUi en Ring 3 y presentacion
por GOP. El laboratorio **RTX FWSEC** conserva su candidato UEFI aislado.
En metal llego a SEC2 `701` y quedo en GSP `804`, con la cola de estado
sin publicar. La aceleracion 3D sigue pendiente. Los ensayos siguientes
describen etapas del laboratorio que quedan como referencia.
En el candidato de inventario PCI, F2 muestra los dispositivos con DMA
habilitado despues de iniciar USB. Esa captura permite preparar sus
mapeos antes de activar AMD-Vi en el equipo fisico.
[Ensayo directo de GPU](docs/NATIVE-DESKTOP-BOOT.md#gpu--nvidia).
El ensayo QEMU mas reciente reserva y relee las 65,536 entradas DTE
despues de ExitBootServices con alias CPU supervisor, de solo lectura y
NX; luego lo revoca. Es preparacion de memoria, no aceleracion: AMD-Vi
sigue apagado, la RTX no recibe DMA y no se emite medio para METAL.
[Evidencia del traspaso DTE](Reports/amdvi-dte-post-ebs-qemu-20261121.json).

El siguiente perfil QEMU de AMD-Vi configura las 65,536 entradas con
denegacion predeterminada, concede dominios separados a EDU, xHCI y AHCI,
invalida los solicitantes presentes y comprueba una transferencia traducida,
su rechazo fuera de rango y la revocacion. Los tres casos QEMU pasaron.
Esto valida el laboratorio virtual; no enciende DMA de la RTX ni acelera
el escritorio fisico. [Evidencia de tabla completa](Reports/amdvi-full-dte-default-deny-qemu-20261121.json).

El siguiente candidato fisico queda aislado en `EFI/BMO-X2/AMDVI-PREFLIGHT.EFI`
y `BMO-X2/GPU-PF`; conserva intactos `NVIDIA.EFI` y los datos de GPU actuales.
QEMU paso 3/3 para FAT32, rechazo W+X y reserva/lectura DTE post-EBS. Esta
prueba deja DMA de la RTX y GSP pendientes. El escritorio METAL del
22-11-2026 mostro `AMDVI_DTE_POST=01 00040000`, que confirma la lectura
de la reserva y la retirada del alias CPU despues de ExitBootServices.
El siguiente paso es verificar el dominio DMA fisico de la RTX.
[Evidencia QEMU del preflight](Reports/amdvi-metal-preflight-qemu-20261121.json) ·
[Pasos para el ensayo METAL](docs/NATIVE-DESKTOP-BOOT.md#preflight-metal-aislado-sin-dma).

El preflight HOST coteja los BDF del censo METAL con los alcances IVRS
leidos ahora de ACPI. El censo guardado queda cubierto por una sola unidad
IVHD: 17 de 17 solicitantes observados, incluidos 15 con Bus Master activo.
La RTX `29:00.0` (`10de:2504`) figura con Bus Master apagado.
Es solo una union estatica; no demuestra DTE, dominios ni invalidacion,
por eso mantiene bloqueada la traduccion fisica. Se regenera con:

```powershell
$py = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py -B tools/host/gpu/ivrs.py --census-json Reports/dma-pci-census-metal-20261120.json --output-json Reports/amdvi-physical-dma-preflight-20261121.json
```

[Matriz de preflight](Reports/amdvi-physical-dma-preflight-20261121.json).

El escritorio ya recibe entrada xHCI en QEMU con teclado y raton en
perfiles separados, mediante el transporte de diagnostico y el servicio
HID Rust de Ring 3. Cada prueba desactiva su alternativa PS/2. No acredita
todavia los USB AMD fisicos ni dos dispositivos USB simultaneos.
[Estado y comandos de USB nativo](docs/NATIVE-USB.md).

RmlUi 6.3 y FreeType ya ejecutan su motor real en Ring 3 bajo QEMU,
con dibujo Rust CPU y accion ULTRA-J nativa. El SBEF del laboratorio
ocupa 1,849,758 bytes. Se probaron Enter, clic PS/2, cierre de recursos,
presentacion de 1,024,000 pixeles y rechazo W+X. El primer cuadro coincide
pixel por pixel con el motor HOST, incluso con atlas nativos mas pequenos.

El heap tiene un limite de 4 MiB y alcanzo 3,028,176 bytes en este ensayo;
el framebuffer separado reserva 4,096,000 bytes. El cargador experimental
de paginas grandes mapea 16 MiB de usuario, incluida la pila: el pico del
heap no es la RAM total del sistema. Este visor es una aplicacion de
prueba separada del escritorio permanente; no acredita USB en METAL.
[Comandos, arquitectura y limites](tools/desktop/rmlui/native/README.md),
[evidencia nativa HOST/QEMU](Ultra-J/evidence/rmlui-native-ring3.json).

La primera sonda del dibujador y el primer build de bibliotecas siguen
registrados como evidencia historica: [dibujador CPL3](Ultra-J/evidence/rmlui-ring3.json)
y [bibliotecas ELF64](Ultra-J/evidence/rmlui-native.json). Las bibliotecas
aisladas conservan dependencias C; el ejecutable nuevo las resuelve con
su runtime acotado, sin enlazar Windows ni servicios Linux.

La sesion C++ de RmlUi ya recibe recursos en memoria, reloj monotono,
destino de dibujo prestado y eventos desde HOST. Tiene entrada por
opacidad, barra animada, transicion de color, movimiento reducido y
callback ULTRA-J probado. El adaptador no llama APIs Windows directamente;
esa entrada HOST sigue separada de la aplicacion nativa. [Sesion y limites](tools/desktop/rmlui/README.md#sesion-c-alimentada-por-host-bmo-ui-memory-v1).

La optimizacion del dibujador guarda los atlas blancos en Alpha8 sin
perder pixeles: el ejemplo retiene 319,488 bytes frente a 1,277,952 en
RGBA. El formato compacto paso la sonda CPL3. La sesion HOST puede
omitir un cuadro preservado en reposo y reactivarse con entrada;
no mantiene un segundo framebuffer. [Medidas y alcance](tools/desktop/rmlui/README.md#memoria-y-reposo-medidos).

El perfil optativo `-Welcome` comprueba la secuencia gato CASM en Ring 0,
bienvenida Rust en Ring 3 y escritorio. Puede saltarse con entrada, que
se conserva para la sesion. No sustituye la verificacion de dispositivos
ni el port de RmlUi. [Recorrido y comandos](userspace/services/desktop/LAYERS.md#gato-ring-0-bienvenida-ring-3-escritorio).

[REPORTES](Reports/README.md) presenta fase, motivo y siguiente paso de
entrada USB, junto con contadores de Ring 0. El perfil de diagnostico
aparece sin teclado ni raton y permite conservar un resumen HOST legible.

BMO-X2 arranca perfiles de prueba independientes en QEMU/OVMF. Hay
evidencia de Ring 0 y Ring 3, escritorio Rust cargado desde SBEF externo,
INVOKE, WAIT y revocacion de paginas. El equipo fisico llega al escritorio,
pero la recepcion de informes de teclado y raton USB sigue pendiente.
El AMD confirmo lectura de descriptores en el puerto 2, con CC 01,
contextos de 64 B y MPS 8. La foto muestra tres puertos conectados.
La [evidencia METAL](Reports/metal-ep0-20261116.json) separa ese avance
de la configuracion HID que falta. La estabilizacion adaptativa
por puerto pasa QEMU. [Prueba y estados visibles](docs/FIRST-BOOT.md#perfil-experimental-de-transporte-xhci).

La nueva fase `--xhci-enum-probe` ya direcciona un dispositivo USB2 y
lee sus descriptores en QEMU, con ajuste de EP0 y parada comprobados.
La lectura de descriptores ya tiene confirmacion fisica en AMD;
todavia no configura endpoints HID. [Prueba de enumeracion AMD](docs/FIRST-BOOT.md#enumeracion-inicial-amd-direccion-y-descriptores).

El servicio de entrada Ring 3 ya procesa los reportes de las sondas USB
QEMU: 260 informes de teclado y movimiento y botones del raton, en perfiles
separados, con CABINA, WAIT y cierre comprobados. Conserva colas acotadas
sin asignacion dinamica. Esto no acredita entrada USB AMD ni un driver
aislado con DMA propio. [Estado, medidas y pendientes](userspace/drivers/usb/DRIVER.md).

## Identidad: NANO-CORE, HOST aislado y Ring 3 abierto

NANO-CORE es el nombre del diseno privilegiado de BMO-X2: un nucleo
acotado que conserva la autoridad de admision, memoria, capacidades,
excepciones y operaciones de CPU y dispositivos que exigen privilegio.
El objetivo es mantener esa base pequena, precisa y auditable mientras
crecen las herramientas y aplicaciones fuera de ella. Es una definicion
del proyecto; la implementacion completa sigue en construccion.

Ring 3 admite diversidad de lenguajes, runtimes, interfaces y servicios.
Cada programa recibe recursos y capacidades acotados. La apertura del
ecosistema se construye ampliando perfiles de admision y servicios,
manteniendo la proteccion entre procesos y respecto del NANO-CORE.
Rust sostiene servicios actuales; C, C++ y ULTRA-J tienen recorridos
de construccion propios. Otros productores requieren su perfil probado.

La portabilidad entre CPUs no es un objetivo ni un requisito de BMO-X2.
Este proyecto se especializa en x86-64. Si se crea una variante para
POWER u otra CPU, sera un proyecto separado con su HOST, backend,
NANO-CORE y pruebas del destino. No se exige un mismo binario entre
arquitecturas ni una capa universal dentro del nucleo.

## HOST y emision hacia el binario del destino

HOST concentra el trabajo de preparacion: analisis, dependencias,
adaptacion al ABI, diagnostico, recursos, verificacion y empaquetado.
Los importadores de formatos y los compiladores permanecen fuera de
Ring 0. Hoy HOST se ejecuta en la maquina de desarrollo; integrarlo
como servicio del propio Ring 3, con aislamiento de sus importadores,
es trabajo pendiente. Una separacion de carpetas no acredita por si
sola aislamiento de memoria o contencion de fallos.

El emisor produce instrucciones y datos del destino con disposicion
definida. CASM emite los perfiles Ring 0 soportados y sus bytes pasan
un verificador independiente. La ruta nativa actual de C, C++ y Rust
conserva el codigo de maquina de su compilador; HOST valida y empaqueta
los perfiles que admite. Un backend nativo total propio y optimizadores
generales de HOST siguen pendientes. No se presentan como implementados.

```text
Fuentes y formatos admitidos
  -> HOST: analizar, resolver, adaptar y diagnosticar
  -> emisor del destino / codigo nativo de un productor admitido
  -> verificacion independiente
  -> SBEF: entrada, regiones, permisos y ABI
  -> NANO-CORE: validar, conceder recursos y activar CPL3
  -> CPU: ejecutar la aplicacion en Ring 3
  -> INVOKE / WAIT: solicitar operaciones y esperar segun el ABI
```

SBEF es el contrato propio que cruza la frontera de admision. El
cargador vuelve a validar sus campos aunque HOST lo haya aceptado.
El NANO-CORE configura los mecanismos del perfil de hardware admitido
y atiende operaciones privilegiadas; la CPU ejecuta directamente el
codigo de usuario autorizado. La cabecera por si sola no resuelve las
llamadas, bibliotecas ni instrucciones de un programa de otro sistema.
HOST debe adaptar o rechazar cada dependencia no satisfecha.

### Maduracion del HOST: x86-64 primero

Cada productor entra por una capa propia. Los lectores, las reglas de formato,
las comprobaciones de seguridad y los servicios se comparten solo donde sus
contratos coinciden. Ring 0 no necesita conocer MSVC, Windows, COFF ni las
bibliotecas de cada toolchain: valida SBEF, memoria y capacidades.

El primer recorrido MSVC prueba un cliente C freestanding, no cualquier
programa de Windows. El manifiesto opcional queda ligado al hash del PE, pero
no prueba que `cl.exe` y `link.exe` lo hayan generado. Imports generales,
runtime C/C++ y carga externa general siguen pendientes.

HOST cambia el contenedor y valida metadatos; no traduce instrucciones x86-64
a otra CPU. El codigo admitido sigue siendo x86-64 y lo ejecuta una CPU x86-64.
Una variante para POWER u otra arquitectura necesita su propio HOST, backend,
ISA y ABI, fuera de este proyecto. El catalogo de capacidades funciona como
una tabla de elementos con estado y limite por formato, ABI, relocacion,
import y runtime ([catalogo x86-64](tools/host/README.md#catalogo-de-capacidades-x86-64)).
El proceso MSVC esta en el [informe QEMU](Reports/host-msvc-qemu.json) y la
[guia HOST](tools/host/README.md#direccion-msvc-hacia-bmo-x2-x86-64).

El presupuesto de 2 KiB corresponde a un nucleo o perfil cuyo contenido
se delimite y mida. Las tablas, pilas, estado, controladores, puentes y
servicios tienen costes propios. La puerta de sesion pequena no prueba
que todo Ring 0, su RAM o el sistema integrado entren en ese presupuesto.

## ULTRA-J: control desde la aplicacion

ULTRA-J existe para facilitar aplicaciones en Ring 3 sin perder el
control del binario, los recursos y el ciclo de vida de los objetos.
La escritura de objetos se inspira en Java y las vistas y estilos
tienen formatos propios. La meta es poder inspeccionar que bytes
ejecuta cada accion, que memoria ocupa y cuando se libera.

La correspondencia binaria empieza en UJBC: cada instruccion tiene
una codificacion definida por version. HOST construye ese bytecode
y el interprete de Ring 3 lo consume. Rust sostiene los servicios
nativos y aporta una referencia de medida para el interprete. El
valor de ULTRA-J se comprueba con aplicaciones mas faciles de
construir y costes de ejecucion que se puedan medir.

QEMU ya verifica una accion externa de 23 B en Ring 3, la limpieza de
su arena y el cierre del panel en el mismo espacio de trabajo. El
siguiente alcance incluye mas objetos, eventos y ventanas antes de
ampliar a aplicaciones graficas mas complejas.
[Contrato UJBC](Ultra-J/FORMAT.md) ·
[Orden de entregas](Ultra-J/README.md#orden-para-madurar-ultra-j) ·
[Medidas y reproduccion](Ultra-J/README.md#comparacion-de-ejecucion-con-rust).

Los servicios, la VM, el compositor y las aplicaciones viven en Ring 3.
El modelo concentra la variedad de aplicaciones y su construccion fuera
de la base privilegiada.

```text
.uj + .ujh + .ujc -> HOST -> bytecode y recursos propios
                                |
                       VM/presentador en Ring 3
                                |
                    INVOKE / WAIT con capacidades
                                |
                    mecanismos de Ring 0

C / C++ / Rust -> compilador y enlace para el ABI de BMO-X2
              -> HOST -> SBEF validado -> cargador Ring 0 -> ejecucion Ring 3
```

El potencial esta en reducir decisiones durante la carga, detectar
incompatibilidades antes del arranque, especializar la emision para el
destino y ampliar Ring 3 sin incorporar cada lenguaje al NANO-CORE.
Compartir runtimes y recursos puede reducir duplicacion. La politica de
capacidades permite mantener distintas aplicaciones bajo la misma
frontera de autoridad. Esas ventajas requieren pruebas: bytes, paginas
de RAM, tiempos de carga y ejecucion, y comportamiento ante fallos.
Cambiar de formato o retirar el requisito de portabilidad no garantiza
por si solo compatibilidad, optimizacion ni seguridad.

Para ampliar esa base faltan enumeracion HID en metal, gestion de
procesos y recursos mas general, eventos de interfaz, texto y fuentes,
layout, bibliotecas de ULTRA-J y medidas completas de RAM y ejecucion.
Un nucleo pequeno necesita tambien controladores y servicios probados.

La familia [drivers de Ring 3](userspace/drivers/README.md) comienza
con una biblioteca USB independiente del compositor. El escritorio
comparte sus decodificadores de teclado y raton; el lector de
descriptores identifica interfaces y endpoints en HOST. El transporte
xHCI de las sondas sigue en Ring 0 y la concesion de DMA directo a
un servicio aislado aun requiere implementar el dominio IOMMU.
[Frontera y pruebas de cierre](contracts/DRIVER-SERVICES.md).

El [puente ULTRA-J para drivers](Ultra-J/README.md#puente-de-registro-de-drivers-en-host)
prepara en HOST el registro por carpetas: identidad PCI, backend SBEF,
recursos solicitados y dependencias. Valida entradas sin conceder
capacidades ni ejecutar el driver; la ruta general de arranque y
aislamiento de servicios sigue pendiente.

## Probar en QEMU

El [backlog de implementacion](docs/RING0-PLAN.md) concentra el trabajo
pendiente sin carpetas ni documentos duplicados por subsistema. Para
comprobar rutas fantasma y referencias explicitas desde la raiz:

```powershell
python -B tools/workspace_audit.py
```

La auditoria es de solo lectura. Distingue enlaces heredados comprobados
por sus hashes y no elimina codigo por carecer de referencias textuales.

Desde la raiz de BMO-X2, con QEMU, Clang y Python disponibles:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion gato-hd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1
```

El primer comando compila el perfil y verifica tres cuadros sin ventana.
El segundo abre el ultimo ensayo aprobado en una ventana QEMU y lo deja
visible. Se puede indicar `-Run .\build\CASM\run-...` para abrir otra
prueba aprobada. El visor usa un snapshot del disco virtual y una copia
de las variables UEFI.

![Cuadro final del gato de arranque en QEMU](kernel/boot/splash/hd/evidence/frame-3.png)

El puente UEFI entrega el framebuffer al perfil CASM tras cerrar
Boot Services. El gato se dibuja como una silueta de 64 por 64 celdas,
ampliadas a 256 por 256 pixeles. Se muestran tres cuadros y la CPU
queda detenida en el ultimo. El escritorio y los atajos de espacios
de trabajo pertenecen al servicio de Ring 3 previsto.
[Detalle grafico](kernel/boot/splash/hd/README.md) |
[Diseno del escritorio](userspace/services/desktop/WORKSPACES.md)

## Avances comprobados

Los pesos de la tabla son bytes de cuerpo y de paquete binario
FAGRAW64. La cabecera mide 24 bytes. El limite de menos de 512 bytes
se aplica a los perfiles de entrada compacta. Las demostraciones mas
grandes usan el limite de 4096 bytes del puente.

| Accion | Cuerpo / paquete | Resultado en QEMU |
|---|---:|---|
| `despertar` | 22 / 46 B | Genesis sale de Boot Services, escribe en pantalla y retorna. [Evidencia](kernel/boot/genesis/evidence/qemu.json) |
| `parada` | 4 / 28 B | Detencion propia en CPL0. [Evidencia](kernel/boot/stop/evidence/qemu.json) |
| `detectar` | 8 / 32 B | CPUID hoja 0 y perfil de CPU observado. |
| `pila` | 50 / 74 B | Seleccion de pila y rechazo de contexto nulo. [Evidencia](kernel/boot/context/evidence.json) |
| `excepcion` | 138 / 162 B | IDT minima y captura de #UD. [Guia](kernel/arch/x86_64/exceptions/FAULT.md) |
| `memoria` | 217 / 241 B | Seleccion y prueba de un marco de 4 KiB. [Evidencia](kernel/mm/physical/evidence.json) |
| `marcos` | 474 / 498 B | Propiedad, agotamiento, devolucion, borrado y reutilizacion de un marco. [Evidencia](kernel/mm/physical/lifecycle/evidence.json) |
| `paginacion` | 473 / 497 B | CR3 propio y alias de usuario de solo lectura y NX. [Evidencia](kernel/mm/virtual/evidence.json) |
| `aislamiento` | 716 / 740 B | Ejecucion en CPL3, #PF de proteccion y borrado de 8 KiB. [Evidencia](kernel/mm/user/evidence.json) |
| `abi` | 1239 / 1263 B | SBEF embebido, INVOKE por SYSCALL y rechazos de ABI ajeno y W+X. WAIT responde -4. [Evidencia](kernel/syscalls/evidence.json) |
| `revocar` | 930 / 954 B | Revoca una pagina, reanuda CPL3 y registra el siguiente #PF. [Evidencia](kernel/mm/virtual/revoke/evidence.json) |
| `gato` / `gato-hd` | 484 / 508 B y 1255 / 1279 B | Tres cuadros verificados. [Evidencia HD](kernel/boot/splash/hd/evidence/qemu.json) |

`-Accion pesos` informa los bytes de codigo, HEX de texto, paquete,
imagenes y ejecucion completa. Las VM usan 256 MiB en las pruebas
del kernel y 1024 MiB en las del gato. La prueba de revocacion usa
36 KiB dentro de la reserva del puente. Los valores de la VM
indican capacidad configurada. La RAM residente del kernel integrado
queda por medir.

En HOST, CASM conserva el resultado de 333 casos diferenciales
frente a la base. SUPER GRAFO registra 124 nodos, 233 relaciones
y 57 elementos del catalogo CASM.
[Medidas CASM](CASM/CONTROL-PERFORMANCE-ELEGANCE.md) |
[Estado del compilador](CASM/STATUS-BMO-X2.md) |
[Catalogo de nodos](super-grafo/CATALOG.md)

## Responsabilidades

| Lugar | Trabajo |
|---|---|
| [CASM](CASM/STATUS-BMO-X2.md) | Fuente, IR, emision x86-64, HEX exacto y verificacion independiente. |
| [kernel](kernel/README.md) | Ring 0 en CASM. Arranque, CPU, memoria, aislamiento, admision SBEF y capacidades. |
| [userspace](userspace/README.md) | Rust como lenguaje principal del runtime, supervisor, servicios y escritorio de Ring 3. |
| [Ultra-J](Ultra-J/README.md) | Lenguaje de aplicaciones de Ring 3 con bytecode, memoria por regiones y vistas binarias. |
| [contracts](contracts/README.md) | ABI, SBEF y fronteras de arranque y ejecucion. |
| [heritage](heritage/README.md) | Procedencia y revision de 110 paquetes Cargo del padre. |
| [tools](tools/README.md) | Build, empaquetado SBEF, diagnostico y pruebas HOST y QEMU. |
| [super-grafo](super-grafo/README.md) | Nodos, dependencias, evidencia y criterios de cierre. |

Rust llevara la base propia de Ring 3. El supervisor decide como
arrancar y recuperar servicios con las capacidades que reciba.
Ring 0 conserva la autoridad sobre memoria, admision y operaciones
privilegiadas. Las aplicaciones de C, C++ y otros lenguajes entran
cuando su binario y runtime cumplen el mismo ABI y SBEF. Python
requiere un interprete portado a Ring 3 que abra los scripts como datos.
[El nucleo de escritorio](userspace/services/desktop/WORKSPACES.md) ya
compone superficies y procesa los atajos de cuatro espacios en pruebas HOST.
Su ejecutable Rust freestanding ya se empaqueta como SBEF ABI 1.
En Windows, `tools/view-desktop.ps1` abre una vista previa interactiva
de los cuatro espacios usando el compositor Rust.
[Reglas de Ring 3](userspace/POLICY.md) |
[Frontera de ejecucion](docs/RING-BOUNDARY.md)

El [ensayo DOOM](userspace/apps/doom/README.md) compila DoomGeneric con GCC,
empaqueta su ELF64 como SBEF ABI 1 y arranca E1M1 en CPL3 tras la intro
del gato. QEMU comprueba el menu y el desplazamiento por teclado.
El perfil QEMU `desktop-doom` arranca el escritorio Rust y permite abrir
CABINA con F2 y escribir `doom run` para iniciar E1M1.
El [mezclador de audio Rust](userspace/services/audio/AUDIO.md) prueba
PCM, volumen y medicion en HOST. La salida virtual y USB quedan pendientes.

## Siguientes entregas

1. **Carga externa.** El cargador CASM valida un SBEF producido por el
   toolchain, mapea sus regiones con permisos y ejecuta la entrada.
   Se prueba una imagen admitida y los rechazos comparados con el lector HOST.
2. **HOST multi-productor x86-64.** Congelar el nivel ISA, crear fixtures
   freestanding y sin imports para MSVC, Clang/LLD, clang-cl/lld-link, GCC y
   Rust; registrar versiones, opciones y hashes desde el build. Definir y probar
   los puentes ABI antes de ampliar imports y runtimes de forma versionada.
3. **Escritorio Rust en Ring 3.** QEMU ya prueba la sesion interactiva con
   composicion por CPU, teclado y espacios en el perfil de ensayo.
   Queda integrarla con el cargador CASM propio y recuperar sus recursos
   al cerrar el proceso.
4. **Ciclo de vida y espera.** WAIT debe bloquear y despertar por senal o
   plazo. Se prueba reutilizar marcos en un segundo proceso antes de
   congelar el ABI de proceso. SMP y DMA requieren confirmacion de revocacion antes
   de reutilizar memoria compartida.
5. **Arranque fisico de prueba.** El primer hito es entrar en Ring 0
   desde el EFI separado en el volumen A: y registrar una parada controlada.
   La FAT32 dedicada junto a PERSONAL es un paso posterior.
   [Orden y evidencia de arranque](docs/FIRST-BOOT.md).

[Plan de Ring 0](docs/RING0-PLAN.md) |
[ABI 1](contracts/ABI.md) |
[Cargador SBEF](contracts/SBEF-LOADER.md) |
[Inventario del padre](heritage/RING3-CRATES.md) |
[Arranque Faggin](contracts/FAGGIN.md)

## Trabajar en el repositorio

```powershell
.\bmo-x2.ps1 -Accion abrir
.\bmo-x2.ps1 -Accion resumen
.\bmo-x2.ps1 -Accion consultar -Consulta nota -Argumentos '{"ruta":"CASM/x86_64"}'
.\bmo-x2.ps1 -Accion mapa
.\bmo-x2.ps1 -Accion comprobar
.\bmo-x2.ps1 -Accion medir
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
.\bmo-x2.ps1 -Accion preparar-grafo
```

El workspace `BMO-X2.sg-workspace` guarda la raiz portable, la vista
Grafo y el Taller CASM. SUPER GRAFO conserva su sesion local y las
posiciones versionadas en `super-grafo/orden.json`. Los ejecutables
HOST y resultados reproducibles viven en `build/`. Se pueden indicar
rutas de herramientas mediante `-Python`, `-Compiler` y `-SuperGrafo`.

El [estado historico](docs/STATUS.md) conserva Genesis y las primeras
medidas del compilador. [Ruta de CASM](docs/CASM-ROADMAP.md) |
[Licencia de la base CASM](heritage/COPYING-CASM)
