# BMO-X2

Hijo de BMO-X. Diseno NANO-CORE para Ring 0 x86-64 en CASM,
HOST separado para construir y admitir binarios del destino,
servicios y aplicaciones en Ring 3, y SUPER GRAFO como mesa de trabajo.
Autor: Eddi Salazar, Lima, Peru.

RmlUi + ULTRA-J ya tienen una vista real HOST. Su dibujador se separo
en Rust no_std y el mismo codigo paso una sonda SBEF en CPL3: 7,085 bytes
de archivo, 12 KiB en regiones RX/R y 4 KiB adicionales de pila de usuario.
Los pixeles coinciden con HOST y se conserva el rechazo W+X. El motor
RmlUi/FreeType completo aun no vive en Ring 3: la DLL Windows tiene
importaciones pendientes de adaptar. [Estado y pasos del escritorio permanente](tools/desktop/rmlui/README.md#para-convertirlo-en-el-escritorio-permanente)
y [evidencia HOST/QEMU](Ultra-J/evidence/rmlui-ring3.json).

Ya existe otra ruta que compila RmlUi, FreeType y libc++ como 282 objetos
ELF64 x86-64, sin convertir la DLL Windows. El enlace relocatable tiene
70 simbolos pendientes y sigue rechazado como ejecutable SBEF. Esto no
mide RAM ni habilita aun el motor completo en Ring 3.
[Build nativo, dependencias y pasos pendientes](tools/desktop/rmlui/native/README.md),
[evidencia de compilacion](Ultra-J/evidence/rmlui-native.json).

La sesion C++ de RmlUi ya recibe recursos en memoria, reloj monotono,
destino de dibujo prestado y eventos desde HOST. Tiene entrada por
opacidad, barra animada, transicion de color, movimiento reducido y
callback ULTRA-J probado. El adaptador no llama APIs Windows directamente;
el runtime C++ enlazado sigue pendiente de portar. [Sesion y limites](tools/desktop/rmlui/README.md#sesion-c-alimentada-por-host-bmo-ui-memory-v1).

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

El presupuesto de 2 KiB corresponde a un nucleo o perfil cuyo contenido
se delimite y mida. Las tablas, pilas, estado, controladores, puentes y
servicios tienen costes propios. La puerta de sesion pequena no prueba
que todo Ring 0, su RAM o el sistema integrado entren en ese presupuesto.

## ULTRA-J y el potencial del conjunto

ULTRA-J aspira a reunir programacion orientada a objetos con escritura
inspirada en Java, estructura de interfaz inspirada en HTML y estilos
inspirados en CSS. Su papel es facilitar aplicaciones y escritorio en
Ring 3. Hoy `.uj`, `.ujh` y `.ujc` implementan subconjuntos propios;
la compatibilidad completa con Java, HTML o CSS no esta implementada.
[Alcance y pendientes de ULTRA-J](Ultra-J/README.md#vision-integrada-y-limites).

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
2. **Escritorio Rust en Ring 3.** QEMU ya prueba la sesion interactiva con
   composicion por CPU, teclado y espacios en el perfil de ensayo.
   Queda integrarla con el cargador CASM propio y recuperar sus recursos
   al cerrar el proceso.
3. **Ciclo de vida y ABI.** WAIT debe bloquear y despertar por senal o
   plazo. Se prueba reutilizar marcos en un segundo proceso antes de
   fijar el ABI. SMP y DMA requieren confirmacion de revocacion antes
   de reutilizar memoria compartida.
4. **Arranque fisico de prueba.** El primer hito es entrar en Ring 0
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
