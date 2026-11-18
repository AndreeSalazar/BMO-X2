# HOST de BMO-X2

## Capas y perfiles x86-64

HOST separa productor, formato, destino y ejecucion. No mantiene un
empaquetador SBEF distinto para cada compilador: MSVC y `clang-cl` pueden
compartir el lector de imagen PE32+; Clang, GCC y Rust comparten el lector
ELF64 cuando producen una imagen estatica que satisface el perfil. El lector
PE no es un importador general de objetos COFF. HOST no infiere la identidad
del productor a partir de PE o ELF. Un manifiesto manual puede declararla y
ligarla al hash del archivo, pero no atesta que ese toolchain produjo los bytes.

```powershell
python -B tools/sbef.py profiles
```

El comando imprime la matriz de productores, lectores, estado de admision,
evidencia de ejecucion y pendientes. Los estados de admision y ejecucion son
independientes: emitir un SBEF admitido no demuestra que el cargador de Ring 3
pueda ejecutarlo. La matriz viva esta en `profiles.py`.

| Capa | Responsabilidad | Limite |
|---|---|---|
| Productor | MSVC, LLVM/Clang, GCC, Rust u otro toolchain; define la evidencia de version, opciones y hashes. | El intake puede ligar un manifiesto manual al hash; la identidad del toolchain no queda atestada. |
| Formato | Un lector compartido para imagen PE32+ o ELF64 estatico. | El lector PE no procesa objetos COFF arbitrarios; PE y ELF tienen reglas de carga distintas. |
| Perfil x86-64 | Admite solo secciones, relocaciones, permisos, imports y limites descritos. | Lo que no tiene semantica BMO-X2 se rechaza con diagnostico. |
| Paquete SBEF | Emite y vuelve a leer el paquete antes de publicarlo. | El paquete no incorpora automaticamente CRT, Win32 ni otros runtimes. |
| Ejecucion invitada | El cargador y los servicios de proceso viven en Ring 3; Ring 0 aplica el contrato y las capacidades. | La admision HOST no acredita el cargador externo generico. |

MSVC PE32+ ya tiene intake y perfiles limitados. LLVM Clang/LLD ELF64 usa el
lector estatico comun. `clang-cl`/`lld-link` puede pasar por el lector PE por
formato, pero aun necesita su propio build registrado y comparacion de salida
antes de declararse productor certificado. GCC y Rust tambien comparten el
lector ELF; sus pruebas concretas no implican compatibilidad con todos sus
programas o bibliotecas. BMO-X2 conserva destino x86-64; otras arquitecturas
requieren otro proyecto y backend, no una carpeta vacia aqui.

## Direccion: MSVC hacia BMO-X2 x86-64

La idea es consumir los artefactos utiles de MSVC y otros productores y
reconstruir su entorno de ejecucion bajo los contratos de BMO-X2. No es
portar el binario MSVC a otra CPU ni copiar Windows. El codigo de maquina
x86-64 se conserva cuando el perfil lo admite; HOST comprueba el contenedor
y lo expresa en SBEF. BMO-X2 aporta sus propias reglas, ABI y servicios en
Ring 3. Ring 0 decide memoria, permisos y capacidades. Una importacion que
no tenga servicio equivalente queda explicada en el informe y se rechaza.

```text
Fuente y dependencias -> productor (MSVC/LLVM/GCC/Rust)
  -> PE32+ o ELF64 x86-64 -> HOST: inspeccion y perfil -> SBEF x86-64
  -> cargador y runtime Ring 3 de BMO-X2 -> NANO-CORE / CPU
```

## Regla de admision por etapas

La secuencia de cierres es obligatoria para declarar compatibilidad general.
Se permite preparar fixtures o prototipos de una etapa futura, pero eso no
salta una puerta ni convierte un ejemplo en soporte general. Los estados,
limites y criterios estructurados se publican con:

```powershell
python -B tools/sbef.py profiles
```

| Orden | Puerta | Estado | Criterio de cierre |
|---:|---|---|---|
| 1 | Cargador externo SBEF | Parcial | CASM valida y mapea SBEF externos, prepara pila/BSS, entra a CPL3 y recupera paginas. QEMU comprueba casos validos, rechazos y concordancia HOST/CASM. |
| 2 | Perfil ISA x86-64 | Pendiente | Congelar instrucciones base, declarar requisitos en SBEF y rechazar por CPUID si la CPU no satisface el perfil. |
| 3 | Fixtures freestanding por productor | Parcial | Muestras sin imports para MSVC, Clang/LLD, clang-cl/lld-link, GCC y Rust; registrar target, versiones, opciones y hashes de forma automatica. |
| 4 | Puentes ABI | Parcial | Definir ABI BMO-X2 y probar Microsoft x64, SysV y los bordes C/Rust, incluidos registros, pila, retorno y errores. |
| 5 | Runtimes e imports versionados | Parcial | Resolver solo servicios publicados; ampliar CRT, memoria, TLS, excepciones, RTTI y bibliotecas por perfil. Rechazar imports desconocidos con codigo, campo y offset. |

Un lector ELF o PE compartido es una pieza de infraestructura, no evidencia
de que todos los productores que emiten ese formato sean compatibles. Del
mismo modo, el manifiesto ligado a hash registra una declaracion; no autentica
por si mismo el compilador. Cada cierre conserva evidencia QEMU y limites.

## Catalogo de capacidades x86-64

Este catalogo es la "tabla periodica" del HOST: elementos pequenos con un
identificador, estado, implementacion y limite. Sirve para combinar formatos,
ABI, relocaciones, imports y runtime por perfiles, sin marcar una capacidad
completa solo porque existe un lector o un fixture.

| Elemento | Estado actual | Limite principal |
|---|---|---|
| MSVC x64 | Fixture QEMU y perfiles parciales | No acepta cualquier programa MSVC ni certifica productor desde el PE. |
| PE32+ | Inspeccion general; empaquetado acotado | No es un cargador completo de EXE/DLL. |
| COFF `.obj` x64 | Fixtures y extraccion confiable limitada | Falta importador y enlace general de objetos. |
| ELF64 estatico | Perfil limitado | El formato aceptado no trae automaticamente su runtime. |
| x86-64 ISA | `x86-64-v1` candidata; no congelada | SBEF aun no declara requisitos de CPU; v2-v4 no se asumen. |
| Relocacion PE DIR64 | Parcial | Solo se permiten destinos internos definidos por el perfil. |
| Imports y runtime | Servicios seleccionados | UCRT, VCRuntime, Win32 general y DLL no estan completos. |
| Carga SBEF externa | Fixtures concretos en QEMU | El cargador generico de procesos Ring 3 sigue pendiente. |

La matriz de maquina vive en `profiles.py` y se exporta como
`CapabilityCatalog` mediante `python -B tools/sbef.py profiles`. En una
variante futura para POWER u otra CPU pueden reutilizarse especificaciones,
formatos neutrales, diagnosticos y evidencia; ISA, ABI, instrucciones,
relocaciones y backend pertenecen al HOST de esa CPU. Este catalogo no afirma que BMO-X2 x86-64
ejecute binarios de otra arquitectura.

El objetivo inicial es x86-64 base. Las extensiones opcionales de CPU se
deben declarar y comprobar por perfil; SBEF aun no codifica esos requisitos.
El mismo nombre x86-64 no garantiza AVX, AVX2 o AVX-512. Antes de declarar
compatibilidad amplia hay que fijar el nivel base, consultar CPUID y rechazar
una imagen que pida funciones no disponibles. Clang documenta niveles
`x86-64-v1` a `v4` y el manual AMD64 describe CPUID: [niveles LLVM/Clang](https://clang.llvm.org/docs/UsersManual.html), [manual AMD64](https://docs.amd.com/api/khub/documents/68GKiN0gMEd6bMddsmhPwg/content).

La maduracion MSVC va por cierres comprobables:

Los pasos siguientes son el trabajo especifico de MSVC. Se pueden preparar
en paralelo, pero el orden maestro de admision anterior gobierna cuando se
puede declarar compatible un productor o runtime de forma general.

1. **Intake y procedencia**: inventario PE32+, hash, directorios y blockers; un
   manifiesto manual puede ligar productor, versiones, opciones y hash exacto.
   El intake de objetos COFF `.obj` y su enlace son un trabajo separado, aun
   pendiente.
2. **PE freestanding**: admitir codigo sin CRT ni imports solo dentro del perfil
   actual y conservar relocaciones que tengan regla definida.
3. **Carga externa en Ring 3**: mapa general de regiones, entry, pila, permisos,
   relocaciones y recuperacion antes de afirmar ejecucion de un SBEF externo.
4. **Imports con contrato**: resolver simbolos contra un catalogo versionado de
   servicios BMO-X2. `/MT` y `/MD` son perfiles distintos; un import ausente
   sigue siendo rechazo explicito.
5. **Runtime C/C++**: incorporar inicializacion, TLS, excepciones, RTTI y otras
   funciones solo cuando exista implementacion y evidencia por servicio.
6. **Win32 y graficos**: GUI, COM, DXGI y DirectX son capas posteriores en
   Ring 3; no forman parte del primer perfil de consola.

El manifiesto de intake es una declaracion del build, no una firma de MSVC.
HOST comprueba que `OutputSHA256` coincide con el PE recibido y conserva la
huella del manifiesto; no demuestra que `cl.exe` o `link.exe` lo hayan creado.
Para inspeccionarlo:

```powershell
.\tools\host\msvc.ps1 -Archivo .\app.exe -Manifiesto .\app.host.json
```

El manifiesto usa `Schema`, `Target`, `Producer`, `Compiler`,
`CompilerVersion`, `Linker`, `LinkerVersion`, `Options` y `OutputSHA256`.
Sin manifiesto el informe marca procedencia como no declarada. Ejemplo de
forma; reemplazar versiones, opciones y hash por los del build real:

```json
{
  "Schema": 1,
  "Target": "x86-64",
  "Producer": "MSVC",
  "Compiler": "cl.exe",
  "CompilerVersion": "version declarada",
  "Linker": "link.exe",
  "LinkerVersion": "version declarada",
  "Options": ["/nologo", "/MD", "/EHsc"],
  "OutputSHA256": "hash SHA-256 de 64 digitos hexadecimales"
}
```

El recorrido integrado se verifico en QEMU: un cliente C freestanding
compilado con MSVC paso por el manifiesto y el intake PowerShell, HOST emitio
el mismo SBEF de 792 bytes que el banco, y ese paquete ejecuto el ABI en CPL3.
INVOKE, rechazo de capacidad, WAIT y recuperacion por fallo pasaron. Esta
evidencia no extiende el perfil a programas MSVC arbitrarios:
[host-msvc-qemu.json](../../Reports/host-msvc-qemu.json).
Para el recorrido actual tambien se compilo el perfil CASM `ring0-abi-probe-0.1`
desde la fuente vigente y pasaron sus cuatro casos QEMU antes de ejecutar MSVC.

El siguiente cierre de ejecucion sigue siendo un cargador externo SBEF general
en Ring 3 y luego un perfil de consola con imports versionados. UCRT/VCRuntime,
Win32, TLS, excepciones, GUI y DirectX se agregan solo con servicios y evidencia
propios.

La sesion visual C++ se construye y prueba en `tools/desktop/rmlui/`.
Su productor HOST empaqueta RML/RCSS, fuentes, UJBC y DLL con hashes;
entrega recursos en memoria al contrato `bmo-ui-memory-v1`. No usa
`pack` como si una DLL Windows fuera SBEF: el lector mantiene su rechazo.
La auditoria separa el objeto del adaptador sin llamadas Kernel32
directas del runtime/STL/FreeType que aun requieren adaptacion.
Ver [sesion, animacion y limites](../desktop/rmlui/README.md).

HOST recibe un ejecutable x86-64 enlazado y decide si cumple el perfil
de aplicacion. El resultado admitido es un SBEF con un ABI, entrada,
regiones y permisos definidos. El ejecutable mantiene el codigo de
maquina que emitio el compilador.

## Frontera con el NANO-CORE

HOST trabaja para el destino x86-64 y fuera del Ring 0 de BMO-X2.
Los importadores, compiladores, resolucion de dependencias y politicas
de construccion pertenecen a herramientas o servicios sin autoridad
privilegiada sobre el sistema invitado. El NANO-CORE conserva la decision
de admitir la imagen y conceder capacidades. Su cargador valida SBEF
de nuevo; un informe favorable de HOST no sustituye esa comprobacion.

La portabilidad entre CPUs no es requisito del proyecto. Una variante
de otra arquitectura tendria herramientas y backend propios en otro
proyecto. La especializacion permite preparar el resultado para un
destino definido, con medidas de tamano, memoria y ejecucion.

La implementacion actual valida perfiles concretos y empaqueta codigo
nativo ya enlazado. El backend propio total, la adaptacion general de
dependencias de otros sistemas, la ejecucion de HOST dentro del Ring 3
de BMO-X2 y el aislamiento de importadores aun estan pendientes. Cuando
se amplie un productor, debe declarar entradas, salida, diagnosticos,
limites de recursos, pruebas de rechazo y evidencia de ejecucion.

| Carpeta o archivo | Responsabilidad |
|---|---|
| `toolchains/abi.py` | Coordinar el banco ABI y cotejar el portal SysV con su vector HEX. |
| `toolchains/msvc.py` | Compilar COFF con MSVC, enlazar el portal Rust Win64 y preparar el cliente PE para el banco. |
| `importers/elf.py` | Validar ELF64 estatico y extraer los segmentos cargables. |
| `importers/pe.py` | Inventariar PE32+, rebajar DIR64 interno y emitir perfiles PE freestanding validados. |
| `importers/pe_imports.py` | Censar DLL, simbolos y ordinales de importaciones normales, con limites de lectura. |
| `importers/pe_bindings.py` | Resolver las importaciones del catalogo del banco MSVC, en la IAT de solo lectura del SBEF. |
| `sbef/format.py` | Definir y validar cabecera, tabla, rangos, permisos y entrada SBEF. |
| `diagnostics.py` | Identificar cada rechazo por codigo, campo, offset e indice cuando aplica. |
| `cli.py` | Leer entradas acotadas y publicar el SBEF solo tras validarlo. |

Los comandos siguen entrando por `tools/sbef.py` y
`tools/abi_toolchain.py`. El [contrato SBEF](../../contracts/SBEF-HOST.md)
describe las opciones. El [ABI](../../contracts/ABI.md) define las
peticiones a Ring 0 y el [cargador](../../contracts/SBEF-LOADER.md)
vuelve a validar el archivo que recibe.

## Banco x86-64

Con `--abi-run`, el banco construye un cliente freestanding, genera
SBEF ABI 1 y lo ejecuta en la sonda CASM de QEMU. Se comprueban
INVOKE, el rechazo de capacidad, WAIT y el borrado de codigo y pila
tras un fallo controlado desde CPL3. `--language cpp` usa el mismo
cliente fuente y `--language rust` usa rustc con el mismo portal ABI.
Cada run guarda la huella de su SBEF y el informe de QEMU.

El reto de 2 KiB exige que `INICIO.X86` contenga en 2048 bytes o menos
la cabecera, la sonda CASM Ring 0 y el cliente SBEF Ring 3. El banco
rechaza un exceso antes de construir la imagen y registra el desglose,
el margen y el total junto con el puente EFI. El primer perfil usa un
cliente y tres llamadas de prueba. El puente UEFI, las tablas, la pila
en RAM, los controladores y el escritorio tienen presupuestos propios.
El comando `pack` admite limites opcionales de archivo y paginas
mapeadas para que cada aplicacion declare su propio presupuesto.

El banco embebe una region RX por cliente. Con `--reuse --abi-run`
ejecuta dos SBEF distintos en las mismas dos paginas de usuario. La
sonda verifica que el codigo y la pila anteriores quedaron desmapeados
y a cero antes de volver a usarlos. El paquete con Clang pesa 1980 bytes.
La etapa de reuso es una extension ensamblada de la sonda CASM. Faltan
el cargador externo general, los propietarios de proceso y la
revocacion de capacidades por proceso.
En la consola x64 de Visual Studio, `python -B tools/abi_toolchain.py
msvc --pe-link link.exe` compila C a COFF, enlaza el portal Rust
`extern "win64"` y entrega un PE32+ x86-64 de inspeccion sin CRT,
DLL importadas ni TLS. El portal traduce los argumentos y el retorno
de Microsoft x64 al contrato INVOKE/WAIT de BMO-X2.

Para recorrer la ruta completa desde la consola x64 de Visual Studio,
con Clang y el target Rust `x86_64-pc-windows-msvc`:

```powershell
python -B tools/abi_toolchain.py msvc --pe-link link.exe --abi-run build/CASM/run-20261112-174958-944cb997
```

El perfil de la sonda enlaza una region RX en `0x40000000`, con entrada
Win64 y metadatos inertes comprobados. HOST extrae el contenido virtual
y descarta cabeceras y relleno de archivo. El directorio de excepciones
admite registros de version 1 sin manejadores ni cadenas. El perfil
rechaza DLL, importaciones, relocaciones, TLS, regiones RW y directorios
fuera de su contrato. Win32 y DirectX requieren servicios propios
en Ring 3. [Evidencia QEMU](../../Reports/abi-msvc-qemu.json).

`--msvc-sections` junto a `--pe-link` y `--abi-run` prueba un segundo
perfil. HOST conserva `.text`, `.rdata` y `.data` con permisos RX,
R y RW. El cargador existente comprueba los permisos y pone a cero
el resto de `.data`. MSVC compila C++17 y `kernel32.lib` del SDK
genera importaciones de `GetTickCount64`, `GetStdHandle` y `WriteFile`.
HOST comprueba la IAT y enlaza los tres servicios Rust del mapa del
enlace antes de emitir el SBEF. El reloj lee los ticks PIT de la sesion
QEMU. La consola admite stdout sincronico por puerto serie.
La prueba confirma el saludo, los bytes escritos, el avance despues de
WAIT y el rechazo de W+X. [Evidencia](../../Reports/abi-msvc-hello-qemu.json).

Con `--msvc-sections --msvc-window` el mismo cliente dibuja un panel y un
triangulo por CPU. El modelo Rust de DIRECTOR compone el panel en una
superficie de 320x200 y la presenta mediante GOP. Super+Q retira el panel
y F1 lo reabre. El banco coteja los tres cuadros en QEMU, incluido el
fondo restaurado. El perfil visual usa `/Od` por el limite de metadatos
unwind encadenados.
[Captura](../../Reports/abi-msvc-director.png) y
[evidencia](../../Reports/abi-msvc-director-qemu.json).

El perfil opcional `guest.py --desktop --usb both --msvc-panel-cc cl.exe`
agrega **Abrir panel MSVC** y F3 al escritorio RmlUi. Para construir su
imagen QEMU se usa `media.py --usb both --msvc-panel`. HOST compila una
unidad de confianza, comprueba que sea una funcion COFF x64 sin
relocaciones ni simbolos externos e incorpora su codigo a la region RX
del SBEF del escritorio. DIRECTOR le asigna su propio identificador
de ventana. RmlUi llama la funcion Win64 y presenta el resultado por CPU.
[Captura](../../Reports/abi-msvc-rmlui.png) y
[evidencia QEMU](../../Reports/abi-msvc-rmlui-qemu.json).
Esta integracion comparte el proceso del escritorio. La admision de
aplicaciones externas en procesos propios y DXGI/Direct3D siguen pendientes.
El boton **Abrir panel MSVC** valida una funcion C++ COFF confiable dentro
del escritorio. Para que HOST inspeccione un `.exe` MSVC se usa el intake
PowerShell descrito arriba.

## Referencia de BMO-X para compatibilidad y graficos

Revision leida del padre: `6076bdefe`. Sus rutas se indican desde la
raiz de BMO-X.

| Componente del padre | Responsabilidad que sirve de referencia |
|---|---|
| `platform/shared/proton-x` | Inspeccion PE32+, reservas, relocaciones e importaciones. El cliente de Ring 3 aporta la memoria y el salto a la entrada. |
| `platform/shared/proton-x-casa` | Exportaciones Win64, incluidas Win32, DXGI y D3D12. Su interfaz `Plataforma` conecta las funciones con reloj, archivos, memoria, ventanas y dibujo. |
| `platform/shared/prometeo` y `platform/shared/verrano-trama` | Representacion de programas graficos, interpretacion y raster por CPU. |
| `platform/shared/verrano/src/dibujo.rs` | Contrato `DrawBackend` y comprobaciones compartidas para los ejecutores. |
| `platform/shared/proton-x-sm86` | Emisor SASS para SM86 y simulador para el banco HOST. La ejecucion en la RTX se verifica por separado. |
| `Ultra_userspace/apps/proton-x` | Carga, resuelve servicios y conecta la presentacion con DIRECTOR. Su censo informa dependencias antes de arrancar el programa. |

El parte `docs/metal/METAL_2026-10-13.md`, seccion 5, registra la intro
de Cyberpunk 2077 a 1280x720 por CPU, alrededor de 16 s por fotograma.
En la corrida medida la RTX dibujo cero lotes del juego. El camino
observado uso las funciones D3D12 de PROTON-X y el dibujo de la casa.
Vulkan figura como otra API posible sobre un backend y tiene su propio
plan en `platform/drivers/gpu/rdna4/PLAN_VULKAN.md`.

La primera adaptacion para BMO-X2 es el censo previo del padre.
`tools/sbef.py probe` muestra las importaciones normales, por DLL y
simbolo u ordinal, aunque el empaquetado quede rechazado. Un censo
invalido se informa por separado con el campo y offset. Se verifico con
un PE enlazado por MSVC que importa `KERNEL32.dll!GetTickCount64` y con
la regresion QEMU del cliente freestanding. No carga DLL ni ejecuta sus
funciones. Las importaciones diferidas conservan su diagnostico propio.

Para inspeccionar un ejecutable MSVC propio desde PowerShell 5.1, compilarlo
en la consola x64 de Visual Studio y pasar su ruta al comando de intake:

```powershell
cl /nologo /MD /EHsc .\app.cpp /Fe:app.exe
.\tools\host\msvc.ps1 -Archivo .\app.exe
```

El intake guarda un informe JSON con el SHA-256, secciones, directorios,
importaciones, relocaciones DIR64 y bloqueos en `build/msvc-intake/`.
No ejecuta el PE. `-Empaquetar` crea un SBEF solo cuando pasa todas las
guardas.

El HOST admite ademas un perfil PE32+ freestanding limitado: EXE de consola,
hasta ocho secciones ordenadas y alineadas a pagina, regiones R/RX/RW sin
W+X, imagen virtual de hasta 16 MiB y SBEF de hasta 1 MiB. Si el ImageBase
cambia, exige DYNAMIC_BASE y relocaciones DIR64 validas que apunten dentro
de las secciones mapeadas. Comprueba relleno, rangos, solapes, entrada,
permisos y los registros de depuracion REPRO/VC_FEATURE. Rechaza por ahora
importaciones/IAT, DLL, TLS, load config, unwind/excepciones y otros
directorios que necesiten semantica de ejecucion.

La prueba real con Visual Studio 2022 compilo
`tools/tests/msvc_rebase_probe.cpp` sin CRT ni DLL. HOST leyo una relocacion
DIR64, rebajo cuatro regiones al espacio SBEF y produjo un archivo de 388
bytes desde un PE de 3072 bytes. El paquete paso `inspect`; la evidencia
esta en [msvc-rebase-intake.json](../../Reports/msvc-rebase-intake.json).
Es una prueba de admision y conversion en HOST, no de ejecucion: el cargador
externo de QEMU descrito en [SBEF-LOADER](../../contracts/SBEF-LOADER.md)
solo admite los perfiles actuales de una a tres regiones con direcciones
fijas. No se afirma que este SBEF generico arranque en QEMU ni en metal.

Para repetir el fixture desde Developer PowerShell x64 de Visual Studio:

```powershell
$out = 'build\msvc-intake\rebase'
New-Item -ItemType Directory -Path $out -Force | Out-Null
cl /nologo /c /O1 /GS- /GR- /EHs-c- /Zl "/Fo$out\rebase.obj" tools\tests\msvc_rebase_probe.cpp
link /nologo /nodefaultlib /subsystem:console /entry:entry /base:0x140000000 /dynamicbase /fixed:no /incremental:no "/out:$out\rebase.exe" "$out\rebase.obj"
.\tools\host\msvc.ps1 -Archivo "$out\rebase.exe" -Empaquetar
$hash = (Get-FileHash "$out\rebase.exe" -Algorithm SHA256).Hash.ToLowerInvariant().Substring(0, 12)
python -B tools\sbef.py inspect "build\msvc-intake\rebase-$hash.SBEF"
```

El ejecutable estandar `/MD /EHsc` sigue rechazado. Su informe actualizado
conserva diez modulos y sesenta simbolos, e identifica imports de CRT/Win32,
load config e IAT en [msvc-standard-intake.json](../../Reports/msvc-standard-intake.json).
El siguiente tramo es definir el cargador generico de varias regiones en
Ring 3 y un mapa versionado de servicios para imports. UCRT, VCRUNTIME,
MSVCP y Win32 se habilitaran uno a uno con semantica y pruebas propias.
Luego vendran TLS, unwind y procesos externos. Win32 GUI, DXGI y Direct3D
siguen siendo trabajo posterior; el intake PE no implementa esas APIs.

El siguiente ensayo debe ampliar la tabla de servicios y comprobar
que cada importacion admitida conserva su semantica. El paso grafico
siguiente es un ejemplo
pequeno con DXGI/D3D12, un ejecutor CPU y una superficie de DIRECTOR.
Para darlo por valido en QEMU se comprueba el cuadro y la finalizacion
de la cola. Vulkan y el emisor SM86 tienen pruebas propias de backend.
