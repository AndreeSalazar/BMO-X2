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
python -B tools/sbef.py profiles --format markdown
python -B tools/sbef.py profiles --producer clang-cl --format markdown
python -B tools/sbef.py probe app.exe --producer clang-cl
python -B tools/sbef.py pack app.elf app.sbef --producer gcc --abi 1
```

El comando imprime la matriz de productores, lectores, estado de admision,
evidencia de ejecucion y pendientes. Los estados de admision y ejecucion son
independientes: emitir un SBEF admitido no demuestra que el cargador de Ring 3
pueda ejecutarlo. La matriz viva esta en `profiles.py`. El selector opcional
`--producer` exige PE32+ para `msvc` y `clang-cl` y ELF64 para `clang`,
`gcc` y `rustc`. El informe registra el perfil declarado y el SHA-256 de la
entrada; `IdentityAttested` queda en `false`.

`ProducerWorkPlan` lista la evidencia y las siguientes pruebas con criterio
de cierre para MSVC, clang-cl, Clang, GCC y rustc. El Markdown detallado de
MSVC conserva el catalogo de capacidades y las dependencias por nivel.
La prioridad es MSVC. clang-cl sirve de control para el mismo ABI Win64.
Clang, GCC y rustc comparten la ruta ELF64 y sus pruebas de carga.

```powershell
python -B tools/sbef.py profiles --producer msvc --format markdown
python -B tools/sbef.py profiles --producer msvc --category tls-exceptions --format markdown
python -B tools/sbef.py profiles --producer msvc --windows-level todos --format markdown
```

| Capa | Responsabilidad | Limite |
|---|---|---|
| Productor | MSVC, LLVM/Clang, GCC, Rust u otro toolchain; define la evidencia de version, opciones y hashes. | El intake puede ligar un manifiesto manual al hash; la identidad del toolchain no queda atestada. |
| Formato | Un lector compartido para imagen PE32+ o ELF64 estatico. | El lector PE no procesa objetos COFF arbitrarios; PE y ELF tienen reglas de carga distintas. |
| Perfil x86-64 | Admite solo secciones, relocaciones, permisos, imports y limites descritos. | Lo que no tiene semantica BMO-X2 se rechaza con diagnostico. |
| Paquete SBEF | Emite y vuelve a leer el paquete antes de publicarlo. | El paquete no incorpora automaticamente CRT, Win32 ni otros runtimes. |
| Ejecucion invitada | El cargador y los servicios de proceso viven en Ring 3; Ring 0 aplica el contrato y las capacidades. | La admision HOST no acredita el cargador externo generico. |

MSVC y `clang-cl`/`lld-link` pasan el cliente ABI Win64 en QEMU. Clang/LLD,
GCC y Rust pasan el cliente ABI por la ruta ELF64. El fixture embebe SBEF v1
en el supervisor de prueba CASM. La [evidencia por productor](../../Reports/host-producers-qemu.json)
registra las huellas verificadas; la carga general de procesos externos
sigue pendiente. BMO-X2 conserva destino x86-64; otras arquitecturas
requieren un backend, ABI, contrato SBEF y NANO-CORE propios. Se podran
reutilizar capas neutrales del HOST y la IR BMO cuando su semantica sea
comun; este proyecto sigue limitado a x86-64.

## Modelo futuro de HOST por ISA

La direccion de crecimiento es compartir adaptadores de productores y una
IR BMO versionada, despues de normalizar y validar la semantica admitida.
La semantica y el formato binario de IR BMO aun no estan implementados;
consulta su [contrato de diseno](../../contracts/IR-BMO.md).
Desde ahi se separan backends por ISA. Cada backend selecciona instrucciones,
convencion de llamadas, relocaciones y requisitos que puede sostener, y emite
el paquete definido para su destino:

```text
productores -> adaptadores -> IR BMO -> backend x86-64 -> SBEF x86-64 -> NANO-CORE x86
                             \-------> backend POWER  -> SBEF POWER  -> NANO-CORE POWER
```

Los perfiles `x86-64-v1` a `v4` describen capacidades de x86-64; no son una
IR ni describen POWER. Una funcion de compilador que requiera una instruccion
o semantica no disponible en el destino debe traducirse de forma definida o
rechazarse con un diagnostico concreto. La IR comun no promete que todo
programa pueda compilar a todas las ISA.

Un PE/ELF ya enlazado contiene codigo maquina para una ISA concreta. El
empaquetador actual puede validar y admitir los casos x86-64 que entiende,
pero no los convierte a POWER. El camino normal a otra ISA requiere fuente o
IR del productor. Traducir un binario x86 existente requeriria un componente
separado para desensamblar, recuperar su flujo de operaciones y traducirlo;
no forma parte del HOST actual.

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
| 1 | Cargador externo SBEF | Parcial | Cierre: integrar en CASM la validacion y el mapeo de SBEF externos, la pila/BSS, entrada CPL3 y recuperacion de paginas; demostrar casos validos, rechazos y concordancia HOST/CASM en QEMU. |
| 2 | Perfil ISA x86-64 | Parcial | Tabla y campo SBEF v2 definidos; falta integrar CPUID/XCR0 en el cargador general CASM y probar niveles con fixtures/QEMU. |
| 3 | Fixtures freestanding por productor | Parcial | Muestras sin imports para MSVC, Clang/LLD, clang-cl/lld-link, GCC y Rust; registrar target, versiones, opciones y hashes de forma automatica. |
| 4 | Puentes ABI | Parcial | Definir ABI BMO-X2 y probar Microsoft x64, SysV y los bordes C/Rust, incluidos registros, pila, retorno y errores. |
| 5 | Runtimes e imports versionados | Parcial | Resolver solo servicios publicados; ampliar CRT, memoria, TLS, excepciones, RTTI y bibliotecas por perfil. Rechazar imports desconocidos con codigo, campo y offset. |

Un lector ELF o PE compartido es una pieza de infraestructura, no evidencia
de que todos los productores que emiten ese formato sean compatibles. Del
mismo modo, el manifiesto ligado a hash registra una declaracion; no autentica
por si mismo el compilador. Cada cierre conserva evidencia QEMU y limites.

La puerta 1 ya tiene un primer artefacto de referencia en HOST:
`python -B tools/sbef.py plan app.sbef` vuelve a validar el paquete y
produce el mapa de usuario por paginas, incluida la inicializacion a cero.
La ruta de CASM aun no consume ni compara ese plan; por eso el cargador
externo sigue parcial y no se marca como cerrado.

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
| x86-64 ISA | Base `x86-64-v1` fijada; SBEF v2 declara v1-v4 | La declaracion no prueba el contenido del binario; la comprobacion general CASM sigue pendiente junto a la puerta 1. |
| Relocacion PE DIR64 | Parcial | Solo se permiten destinos internos definidos por el perfil. |
| Imports y runtime | Consola, DLL fija, ciclo de vida y TLS estatico tienen bancos QEMU | Los runtimes y servicios Win32 generales siguen pendientes. |
| Carga SBEF externa | Fixtures concretos en QEMU | El cargador generico de procesos Ring 3 sigue pendiente. |

La matriz de maquina vive en `profiles.py` y se exporta como
`CapabilityCatalog` mediante `python -B tools/sbef.py profiles`. En una
variante futura para POWER u otra CPU pueden reutilizarse especificaciones,
formatos neutrales, diagnosticos y evidencia; ISA, ABI, instrucciones,
relocaciones y backend pertenecen al HOST de esa CPU. Este catalogo no afirma que BMO-X2 x86-64
ejecute binarios de otra arquitectura.

### Inventario detallado de MSVC

El inventario enumera 69 capacidades en siete categorias. Cada
entrada indica si HOST puede inspeccionarla o emitirla, si un banco
QEMU la ejecuto o si queda pendiente. Los casos QEMU enlazan al
informe original.

| Selector | Contenido |
|---|---|
| `build` | Compilador, enlazador, COFF, bibliotecas, manifiesto y depuracion. |
| `image` | PE32+, secciones, memoria, reubicaciones e ISA. |
| `directories` | Los 16 directorios PE y los bloqueos del perfil base. |
| `imports` | Consola, IAT, DLL fija y carga dinamica. |
| `runtime` | ABI Win64, entrada, ciclo C++, CRT, STL y RTTI. |
| `tls-exceptions` | TLS, excepciones, unwind, SEH y CFG. |
| `system` | Servicios Win32, UI, COM y APIs graficas. |

```powershell
python -B tools/sbef.py profiles --producer msvc
python -B tools/sbef.py profiles --producer msvc --format markdown
python -B tools/sbef.py profiles --producer msvc --category tls-exceptions --format markdown
python -B tools/sbef.py profiles --producer msvc --windows-level todos --format markdown
python -B tools/sbef.py profiles --producer msvc --windows-level avanzado
```

El Markdown usa enlaces relativos a la raiz del repositorio.
Para inspeccionar un EXE propio y obtener sus bloqueos del perfil
base, usa `python -B tools/sbef.py probe app.exe --producer msvc`.

`--windows-level` acepta `base`, `intermedio`, `avanzado` y `todos`.
La lista incluye dependencias de proceso y CRT, escritorio y COM, red y
criptografia, graficos 3D, audio, video y WinRT.
`ImportCoverage` clasifica las importaciones PE normales y muestra los
simbolos pendientes, incluidos ordinales y DLL sin clasificar. Los
prefijos de API sets sirven para agrupar contratos. La resolucion de
API sets, los imports diferidos y la carga dinamica quedan pendientes.
`FixtureSymbols` registra coincidencias por nombre con los tres servicios
de consola del fixture `win64-console-v1`. El resultado de admision del
perfil base se lee en `CanPack` y `Blockers`.

`Admission` explica los bloqueos y sus requisitos, muestra los datos
observados en IAT y `load_config` y agrupa los simbolos pendientes por
servicio. Tambien identifica los destinos que ya existen en perfiles de
prueba acotados. Una coincidencia de nombre en un banco aporta evidencia
para ese perfil. El PE examinado sigue necesitando su propio enlace.

```powershell
python -B tools/sbef.py probe app.exe --producer msvc --format markdown
python -B tools/sbef.py --json-errors pack app.exe app.sbef --abi 1 --producer msvc --explain
```

El segundo comando adjunta `Admission` al rechazo del empaquetador PE
base y conserva su codigo, desplazamiento y salida de error.

### Banco de aplicaciones Windows x64

`tools/tests/windows_apps.py` ejecuta binarios locales en Windows y comprueba
`probe` y `pack --abi 1` para cada PE. El informe JSON conserva el inventario
de imports y el rechazo del empaquetador. Un rechazo debe coincidir con el
inventario y el directorio de prueba debe quedar sin un SBEF parcial.

```powershell
python -B tools/tests/windows_apps.py --sqlite-msvc $sqliteMsvc --sqlite-clang-cl $sqliteClangCl --minigzip-msvc $gzipMsvc --minigzip-clang-cl $gzipClangCl --tar (Get-Command tar.exe).Source --seven-zip $sevenZip --notepad-plus-plus $notepadPlusPlus
```

Los dos binarios de SQLite son obligatorios. El banco comprueba 1000 filas,
rollback, reapertura, integridad y rechazo de una clave duplicada.
`minigzip` comprueba la ida y vuelta de datos binarios. Los archivadores
recuperan un directorio con un nombre Unicode y un archivo vacio. Notepad++
se inventaria estaticamente. El informe corresponde a Windows y HOST,
con ejecucion QEMU pendiente para estos binarios.

El perfil de prueba `win64-console-heap-v1` liga `GetProcessHeap`,
`HeapAlloc`, `HeapReAlloc` y `HeapFree` al runtime Rust. Usa una arena
privada de 64 KiB con bloques alineados a 16 bytes. El banco comprueba
asignacion, relleno cero, realojamiento con datos conservados, crecimiento
en sitio, identificadores invalidos, agotamiento y reutilizacion.
`HeapSize` consulta el tamano de un bloque activo y rechaza punteros
interiores y bloques liberados.
[Evidencia en QEMU con MSVC y clang-cl](../../Reports/host-win64-heap-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-heap
```

El perfil `win64-package-file-v1` incorpora `CreateFileW`, `ReadFile`,
`CloseHandle`, `GetLastError`, `GetFileType` y `GetFileSizeEx` para un
archivo de entrada empaquetado en una region de solo lectura del SBEF.
Las consultas distinguen el archivo y stdout, verifican el tamano sin
mover el cursor y rechazan handles cerrados. `SetFilePointerEx` admite
posiciones relativas al inicio, al cursor y al final, con una posicion
maxima acotada. Es un perfil sincrono de un solo
hilo con un handle abierto a la vez. El banco comprueba lectura parcial,
fin de archivo, reapertura desde el inicio y rechazo de handles caducados.
[Evidencia en QEMU con MSVC y clang-cl](../../Reports/host-win64-package-file-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-package-file
```

El banco de GZIP compila `inflateBack` y `deflate` desde zlib para ambos
productores. El cliente lee una entrada GZIP empaquetada, verifica su
longitud y CRC-32, rechaza una copia con el CRC alterado y vuelve a
comprimir los bytes en Ring 3. El perfil `win64-scratch-file-v1` escribe
el GZIP resultante mediante `WriteFile` en `output.bin`. El archivo vive
en una arena volatil de 4 KiB del proceso. La prueba lo reabre, valida
sus bytes y lo trunca con
`CREATE_ALWAYS`. Tambien verifica accesos invalidos y que un intento de
escritura sin espacio conserva los datos y la posicion.
El banco tambien prueba sobreescritura sin truncar, truncado y extension
con `SetEndOfFile`. Los huecos del archivo de RAM se inicializan a cero.
`FlushFileBuffers` valida el acceso de escritura del archivo en RAM.
QEMU captura el GZIP resultante y el HOST lo descomprime para comparar
los bytes con la referencia. El lector del cliente admite un miembro
sin campos opcionales. Un tercer caso carga exactamente 65536 bytes de
SBEF y comprueba la limpieza del area de staging y del mapa temporal.
[Informe de GZIP y comparacion con minigzip en Windows](../../Reports/host-win64-gzip-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-gzip $zlibSource
```

El CLI adaptado `minigzip` toma su vector de argumentos de la seccion de
solo lectura del SBEF. Soporta `-c`, `-d`, niveles `-1` a `-9` y la
entrada empaquetada `input.bin`. El banco ejecuta compresion, descompresion,
CRC invalido y argumentos invalidos con ambos compiladores. Los dos casos
de error comprueban el codigo de salida y stdout vacio.
[Informe del CLI adaptado y contraste con minigzip en Windows](../../Reports/host-win64-minigzip-cli-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-minigzip $zlibSource
```

Para usar archivos locales, el HOST empaqueta una entrada por arranque y
guarda la salida binaria de QEMU tras validar el codigo de salida y los
bytes. La publicacion exige una ruta nueva y una carpeta existente en un
sistema de archivos con enlaces duros. El archivo intermedio se elimina
si falla la publicacion.
[Informe de compresion y reapertura en dos arranques QEMU](../../Reports/host-win64-minigzip-files-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-minigzip $zlibSource --input-file datos.bin --output-file datos.gz --level 9
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-minigzip $zlibSource --input-file datos.gz --output-file recuperado.bin --decompress --minigzip-producer clang-cl
```

El banco de disco virtual usa una imagen IDE secundaria exclusiva de
QEMU. El cliente MSVC comprime en Ring 3 y el supervisor publica un
registro GZIP en el sector 1 con `FLUSH CACHE`. En otro arranque, el
cliente clang-cl lee el mismo sector y recupera los datos sin recibir una
entrada empaquetada. El banco compara todos los demas sectores, verifica
que la lectura conserva la imagen y prueba un CRC alterado en una copia.
Este transporte de prueba admite 504 bytes de GZIP en un sector.
[Informe de escritura y lectura en arranques QEMU separados](../../Reports/host-win64-minigzip-disk-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-minigzip-disk $zlibSource
```

El perfil FAT16 crea `OUTPUT.GZ` en el directorio raiz. Asigna clusters
libres, escribe el GZIP, actualiza las dos copias FAT y publica la
entrada de directorio. Un segundo arranque busca el mismo nombre y
recupera los datos siguiendo una cadena fragmentada. El HOST verifica
los cambios byte a byte en la imagen, incluidos ambos espejos FAT y
la conservacion de los archivos vecinos. El reemplazo escribe otra
cadena, publica la nueva entrada y luego libera la cadena anterior.
Otro arranque comprueba los bytes del reemplazo. Las pruebas negativas
cubren CRC alterado, nombre ausente, cadena ciclica, creacion con nombre
existente y falta de clusters libres. Cada control usa una copia separada.
[Informe de OUTPUT.GZ en QEMU](../../Reports/host-win64-minigzip-fat-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-minigzip-fat $zlibSource
```

El perfil admite hasta cuatro clusters de 512 bytes por archivo y opera
sobre una raiz y un grupo de clusters acotados. La publicacion requiere
espacio libre para la copia nueva. Los sectores 78 y 79 guardan copias
del registro con CRC antes de modificar los datos. Al reabrir, la
entrada de directorio determina que cadena conservar. Si solo una copia
del registro es valida, el invitado la usa para reconciliar la FAT y
borra las dos copias al terminar.

El banco detiene una ejecucion entre las dos escrituras FAT y otra
despues de publicar el directorio. Sobre copias de esas imagenes, el
banco simula escrituras parciales en cada copia del diario, un enlace
FAT, los campos de cluster inicial y tamano del directorio y un sector
GZIP. El diario contiene el CRC de ambas versiones. El escritor verifica
la copia nueva antes de publicarla. Si al reiniciar sus datos estan
incompletos o los campos del directorio mezclan ambas versiones, el
invitado vuelve a la copia anterior tras verificar su CRC. Dos copias
de diario invalidas o dos cargas GZIP danadas producen un rechazo sin
cambios en el disco. El perfil conserva el nombre y los demas campos
de la entrada y opera sobre el volumen virtual del banco.

El perfil de arranque `win64-process-start-v1` enlaza
`GetCommandLineW`, `GetCommandLineA`, `GetACP`, `GetStartupInfoW`,
`GetLastError`, `SetLastError` y `ExitProcess` en la IAT de solo
lectura. QEMU comprueba las dos representaciones de la linea de
comandos, incluida la pagina de codigos UTF-8 65001 del perfil.
La estructura `STARTUPINFOW` Win64 ocupa 104 bytes y devuelve los
valores por defecto de la sesion. El estado de error se comparte
con los servicios de archivos en esta sesion de un hilo. El supervisor
registra el DWORD completo y rechaza valores mayores a 32 bits.
El mismo perfil comprueba `TlsAlloc`, `TlsGetValue`, `TlsSetValue` y
`TlsFree` con 64 indices dinamicos. Las pruebas cubren valores nulos,
agotamiento, reuso, indices fuera de rango y el efecto de
`TlsGetValue` sobre LastError. Tambien cubre `InitializeSListHead`
con una cabecera Win64 alineada de 16 bytes. El runtime de esta prueba
corre un solo hilo. El banco de TLS estatico de dos hilos usa un
perfil distinto.
El perfil admite 128 indices FLS en el contexto de ejecucion actual. QEMU
verifica que liberar un indice con un valor ejecuta su callback una sola
vez y que `ExitProcess` ejecuta el callback pendiente antes de entregar
el codigo de salida al supervisor. La sonda usa un unico contexto FLS.
[Contrato de callbacks FLS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/nc-winnt-pfls_callback_function).
[Informe del arranque Win64 y admision del PE original](../../Reports/host-win64-process-start-qemu.json).

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-process
```

El ejecutable Windows distribuido requiere su arranque CRT, mas memoria
de carga y mas servicios Win64. El perfil adaptado usa entradas y salidas
de hasta 4 KiB, lee del paquete y emite por stdout. La persistencia de este
flujo la realiza el HOST en Windows. La IAT
resuelta queda de solo lectura. El cargador debe interpretar o rechazar
explicitamente las caracteristicas declaradas en `load_config`.

### Ruta del PE original de minigzip

El HOST compila cuando recibe fuentes. Cuando recibe el EXE, inspecciona
el PE, valida los metadatos y prepara su paquete SBEF. Los servicios
Win64, el estado del proceso y el arranque CRT corresponden al cargador
y al runtime Ring 3 de BMO-X2. El supervisor arbitra el mapeo y los
servicios que requieren privilegios.

Wine ofrece dos referencias de implementacion. Su cargador recorre los
descriptores de importacion y resuelve dependencias antes de entregar
el control al ejecutable. Sus API de TLS separan la asignacion de
indices del proceso de los valores de cada hilo.
[Cargador de Wine](https://github.com/wine-mirror/wine/blob/master/dlls/ntdll/loader.c)
[TLS de Wine](https://github.com/wine-mirror/wine/blob/master/dlls/kernelbase/thread.c).

Los dos PE originales importan 80 simbolos de `KERNEL32.dll`.
Hay 31 destinos con evidencia en perfiles acotados y 49 pendientes.
El informe de QEMU registra ambos hashes y los nombres por area.
Los PE declaran 241664 bytes (MSVC) y 258048 bytes (clang-cl) de imagen.
El lector FAT32 y el supervisor de QEMU aceptan hasta 262144 bytes de
archivo SBEF. El banco del proceso verifico paquetes de 242999 y
242849 bytes con MSVC y clang-cl, incluyendo la lectura del extremo de
la region de solo lectura y el borrado del area temporal. Cada caso
uso 63 de 64 marcos de usuario. El presupuesto de marcos para la imagen
original depende de las secciones, el runtime integrado y la pila.

La admision del original requiere resolver la IAT contra el runtime
integrado y publicarla de solo lectura, inicializar la cookie de
seguridad y aplicar el contrato CFG declarado en `load_config`. El
resultado se valida con el PE original en QEMU, registrando el codigo
de salida y comparando los bytes tras comprimir y descomprimir.

Para registrar compatibilidad en QEMU, conservar el hash del PE y del
SBEF, la salida de consola, el codigo de salida y la evidencia del
resultado. Para `minigzip`, comprobar la igualdad del SHA-256 tras
descomprimir. Para SQLite, exigir `1000|1001000` en memoria y luego
`integrity_check = ok` con los mismos datos tras abrir la base en un
segundo proceso. Los PE de SQLite inspeccionados superan 1.5 MiB de
`SizeOfImage`. El banco QEMU actual tiene 64 paginas de usuario, por lo
que la prueba del CLI completo requiere ampliar el presupuesto verificado
de carga, ademas de implementar sus dependencias.

El destino de BMO-X2 es exclusivamente x86-64. La base fijada es
`x86-64-v1`; cada SBEF v2 declara el minimo `v1`, `v2`, `v3` o `v4`. El
codigo de las sondas LLVM compara ese requisito con CPUID y con el estado
habilitado por el sistema (`CR4.OSFXSR` y `XCR0` cuando corresponda). La
sonda externa `stage_desktop_media.py --sbef-isa` verifica en QEMU un
SBEF v2 v1 y el rechazo de un requisito v3 con `qemu64`, junto con los
rechazos W+X y de campo reservado. La matriz completa v1-v4 y la integracion
productiva CASM siguen pendientes. La declaracion no desensambla instrucciones:
cada productor debe usar opciones de compilacion coherentes y aportar
fixtures. Extensiones de fabricante o fuera de estos niveles quedan sin
declarar. La jerarquia v1-v4 sigue los niveles de microarquitectura del
[x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI/blob/master/x86-64-ABI/low-level-sys-info.tex).

## Estado de MSVC y C++

**Objetivo actual**. Ejecutar en Ring 3 un programa de consola C++ con la
entrada estandar de MSVC. Hoy el cliente C++ de prueba arranca con la
entrada de BMO-X2, usa funciones de la UCRT de Microsoft y pasa los casos
de `/GS` y unwind descritos abajo.

**C++ es la prueba principal.** Con `cl.exe` y `link.exe` podemos cubrir
constructores, destructores, plantillas, TLS y excepciones en el mismo
recorrido. Las sondas pequenas en C comprueban el ABI y ayudan a localizar
fallos de carga. `clang-cl` y `lld-link` sirven como control independiente
para el mismo formato PE32+ y el ABI Microsoft x64. HOST recibe el EXE
enlazado y valida su perfil, sus metadatos y sus dependencias.

| Tramo | Estado actual | Evidencia |
|---|---|---|
| PE32+ x86-64 | HOST inventaria directorios, imports, IAT, unwind y `load_config`. Empaqueta perfiles acotados y relocaciones DIR64 internas. | [Intake de un EXE /MD](../../Reports/msvc-standard-intake.json) y [DIR64 en QEMU](../../Reports/host-msvc-rebase-qemu.json) |
| Carga SBEF en Ring 3 | QEMU carga clientes externos desde FAT32, comprueba permisos y limpia el mapa al salir o fallar. La reapertura de procesos independientes en el mismo arranque sigue pendiente. | [Consola MSVC](../../Reports/host-msvc-console-qemu.json) |
| Runtime C++ acotado | Cliente `/MT` con entrada BMO-X2. Ejecuta constructores, cierre C++ y siete funciones de `libucrt.lib`. | [CRT y /GS en QEMU](../../Reports/host-msvc-crt-gs-native-qemu.json) |
| DLL y TLS | DLL fija con attach y detach. Plantilla TLS estatica comprobada en dos hilos del banco. | [Ciclo de DLL](../../Reports/host-msvc-dll-lifecycle-qemu.json) y [TLS](../../Reports/host-msvc-tls-qemu.json) |
| Excepciones Win64 | El banco QEMU entrega `#UD`, reconstruye dos marcos y prueba filtros SEH de MSVC en el llamador inmediato y un marco superior. | [Evidencia en Ring 3](../../Reports/host-msvc-crt-gs-native-qemu.json) |
| EXE Windows con arranque estandar | El EXE `/MD /EHsc` del banco sigue bloqueado por imports, IAT y `load_config`. Requiere 60 simbolos de 10 DLL. | [Diagnostico del EXE](../../Reports/msvc-standard-intake.json) |

### Pruebas de cierre

| Paso | Que tiene que pasar |
|---|---|
| **1. Completar unwind Win64** | El banco detecta epilogos `add`/`lea`, `pop`/`ret` y un salto indirecto RIP-relativo. El manejador recibe `CONTEXT_FULL` y un registro de excepcion. Falta extender ambas rutas a un despacho general. |
| **2. Probar SEH y C++** | El banco ejecuta filtros en dos marcos y un `__finally` durante el desenrollado. Faltan la cookie `/GS` por proceso y `throw`/`catch` con destructores. |
| **3. Arrancar C++ con `/MT`** | Ejecutar un EXE por la entrada estandar de MSVC con argumentos, heap, stdout, `main` y cierre comprobados. Abrirlo, cerrarlo y volverlo a abrir en el mismo arranque. |
| **4. Arrancar C++ con `/MD`** | Resolver las DLL y los API sets de la muestra, aplicar sus requisitos de IAT y `load_config` y completar su ejecucion con salida verificable. |
| **5. Probar una aplicacion Win32** | Abrir archivos y responder a ventanas y eventos. GUI, COM y graficos se verifican con sus propios clientes y contratos. |

La [regla de admision](#regla-de-admision-por-etapas) fija los requisitos
para declarar compatibilidad general. El [catalogo de MSVC](#inventario-detallado-de-msvc)
permite consultar cada capacidad y su evidencia.

### Procedencia del ejecutable

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

`tools/sbef.py profiles` publica el perfil `win64-console-v1` en
`RuntimeImportProfiles`. En el banco `--msvc-console`, MSVC y Rust generan
el PE32+, el mismo enlazador de imports publica una IAT de solo lectura y
HOST emite un SBEF v2. QEMU lo carga desde FAT32 en un espacio de Ring 3
propio. Se comprueban el reloj, el vencimiento de WAIT, la escritura de
39 bytes, el rechazo de un descriptor invalido y el cierre por SYSCALL.
HOST rechaza `KERNEL32.dll!OtherFile` antes de crear la imagen de QEMU.

```powershell
$validatorRun = 'build/CASM/run-del-validador'
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-console
```

El ensayo usa MSVC x64, Windows SDK, LLVM y el destino Rust Win64.
El perfil se elige al construir el banco y su catalogo contiene tres
imports. Sigue pendiente una ruta de carga para DLL y CRT generales.
[Evidencia del proceso de consola](../../Reports/host-msvc-console-qemu.json).

`--msvc-dll` construye un EXE y una DLL freestanding con MSVC y usa el
comando publico de HOST para enlazar el import `module.dll!BmoStep`.
El EXE y la DLL ocupan seis regiones en el mismo SBEF. El banco verifica
dos llamadas al modulo, un rechazo HOST por exportacion ausente y un
fallo de pagina cuando el modulo intenta escribir en su region marcada R.

```powershell
$validatorRun = 'build/CASM/run-del-validador'
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-dll
python -B tools/sbef.py pack dll-client.exe dll-client.sbef --abi 1 --producer msvc --with-dll module.dll
```

El segundo comando toma los dos PE que el primer comando deja en la
carpeta del run. El perfil `win64-fixed-dll-v1` resuelve una exportacion
directa de una DLL fija sin inicializador. La carga dinamica queda
pendiente. [Evidencia EXE y DLL](../../Reports/host-msvc-dll-qemu.json).

`--msvc-dll-lifecycle` construye el EXE con el arranque Win64 de BMO-X2.
HOST coteja `BmoDllEntry` con la entrada PE de la DLL. La secuencia es
attach, constructores MSVC de `.CRT$XC*`, cliente, callbacks `atexit`
en orden inverso, detach y salida por SYSCALL. El arranque guarda hasta
16 callbacks en esta sesion de un solo hilo. La prueba comprueba dos
constructores y dos destructores de C++ antes del detach. Si el attach
devuelve cero, el cliente y sus constructores quedan sin ejecutar.
La prueba usa `/Od` para el arranque y el cliente con las reglas de
unwind admitidas por HOST. UCRT, VCRuntime, TLS, excepciones y carga
dinamica siguen pendientes.

```powershell
$validatorRun = 'build/CASM/run-del-validador'
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-dll-lifecycle
```

[Evidencia del arranque Win64](../../Reports/host-msvc-dll-lifecycle-qemu.json).

### Funciones de la UCRT estatica

`--msvc-crt` compila un cliente C++ con MSVC `/MT` y entrada BMO-X2. El
enlazador extrae `abs`, `llabs`, `strlen`, `strcmp` y `strncmp` de la
`libucrt.lib` x64 del Windows SDK. El banco exige que el mapa de enlace
atribuya las cinco funciones a la biblioteca y registra el hash del PE
y de la biblioteca.

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-crt
```

El SBEF se carga desde FAT32 en QEMU. El constructor de C++ usa la UCRT,
el cuerpo comprueba las funciones y el cierre comprueba el orden inverso
de `atexit` y del destructor. El cliente escribe
`MSVC CRT: inicio, main y cierre OK` y termina con codigo cero. El banco
comprueba la limpieza de las paginas y la restauracion del mapa.
[Evidencia QEMU](../../Reports/host-msvc-crt-qemu.json).

El arranque usa `crt_startup.cpp` de BMO-X2. Siguen pendientes el arranque
normal de Microsoft, las bibliotecas dinamicas de `/MD` y la CRT general.
Con el SDK 10.0.26100.0, `strspn` y `strcspn` exigen
`__security_cookie`, `__security_check_cookie` y `__GSHandlerCheck`.
El banco de MSVC descrito abajo acredita sus llamadas normales en CPL3.

### Comprobacion de cookie Win64

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-crt-gs
python -B tools/sbef.py probe app.exe --producer msvc
```

El banco construye el cliente con `cl.exe /GS` y revisa las referencias
COFF. Cuando el compilador requiere `__GSHandlerCheck`, recompila el
cliente con `clang-cl /GS` para comprobar la llamada de epilogo
`__security_check_cookie` con el ABI Win64. Conserva el arranque BMO-X2
compilado por MSVC y las mismas funciones de `libucrt.lib`.
La semilla de prueba se genera en HOST y queda embebida en la imagen.
La inicializacion con entropia por proceso sigue pendiente.

El control cambia un selector RW de la misma imagen. El cliente modifica
la cookie de referencia despues de guardar su copia en la pila. QEMU
comprueba el aborto en CPL3, stdout vacio y la limpieza del mapa. El caso
normal comprueba la salida de consola y el codigo cero.
[Evidencia QEMU](../../Reports/host-msvc-crt-gs-qemu.json).

### MSVC /GS con libcmt y UCRT

```powershell
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-crt-gs-native
```

Este banco usa `cl.exe /GS`. Enlaza `strspn` y `strcspn` desde
`libucrt.lib` y extrae `gshandler.obj` y `amdsecgs.obj` de
`libcmt.lib` para conservar el manejador y el verificador de Microsoft.
La ruta de fallo llama a `__report_gsfailure` del banco, que aborta en
CPL3. La semilla de prueba se incorpora durante el build.

El empaquetador interno conserva `.pdata` y `UNWIND_INFO` en lectura
sola. Comprueba los RVA ejecutables de `__GSHandlerCheck` y del
manejador SEH del banco en el MAP. Las cadenas apuntan a entradas
anteriores ya comprobadas. Verifica el rechazo de un destino distinto y el
rechazo de la misma imagen por `pack` normal.

El banco llama a `__GSHandlerCheck` desde un marco vivo generado por MSVC.
Captura el PC y RSP del llamador, busca su entrada en `.pdata` y usa
`UNWIND_INFO` para localizar el manejador y sus datos. Solo admite el
marco fijo de esta prueba, con `UWOP_ALLOC_SMALL` y posibles
`UWOP_PUSH_NONVOL`. El caso valido verifica `ContinueSearch`. El
control con cookie alterada exige un aborto dentro del manejador, con un
recibo distinto al del epilogo.

El mismo banco provoca un `#UD` real con `UD2` en Ring 3. HOST fija
el PC de la instruccion y el del destino del mismo segmento RX. El
supervisor coteja PC, selectores y rango de pila. Guarda los registros
volatiles, los selectores y RFLAGS en un bloque de 80 bytes en la pila
del cliente. Regresa mediante `iretq` con RIP, RSP y vector 6.
La entrada en Ring 3 completa la captura con los registros no volatiles
y `FXSAVE64`. Se usan `CONTEXT`, `EXCEPTION_RECORD` y
`DISPATCHER_CONTEXT` del Windows SDK para la llamada a `__GSHandlerCheck`.
El cliente comprueba los siete registros volatiles, CF, CS, SS, XMM0 y
XMM6. Se registra `EXCEPTION_ILLEGAL_INSTRUCTION` con el RIP original.
El codigo de destino recupera el marco MSVC que llamo a la funcion
hoja y ejecuta `__GSHandlerCheck`. Un segundo `#UD` en el mismo proceso
termina el proceso sin entregar el manejador otra vez.

Cuando el manejador devuelve `ContinueSearch`, el banco recorre dos
marcos vivos desde la captura de RIP, RSP, los registros enteros no
volatiles y XMM6-XMM15. Lee `.pdata` y `UNWIND_INFO` para deshacer
`UWOP_ALLOC_SMALL`, `UWOP_ALLOC_LARGE` escalado, `UWOP_PUSH_NONVOL`,
`UWOP_SAVE_NONVOL` y `UWOP_SAVE_XMM128`. El segundo marco guarda R12
en un fragmento encadenado y recupera RBX y XMM6 desde el marco
principal. El recorrido coteja RIP, RSP, RBX, RSI, RDI, R12 y los 128
bits de XMM6 con valores conocidos antes de la llamada.

El llamador establece RBP a 128 bytes de la base fija con
`UWOP_SET_FPREG` y reserva otros 64 bytes en el cuerpo de la funcion.
El recorrido usa RBP para localizar el marco y compara RSP antes y
despues de deshacerlo. Una cadena con desplazamiento de RBP distinto
del registro principal se rechaza.

Cada lectura de pila se limita a la pagina del cliente. Una cadena
solo puede apuntar a una entrada anterior de `.pdata` y se sigue hasta
ocho registros. Un opcode desconocido y una cadena que no coincide con
la tabla producen codigo 1 y stdout vacio. La prueba positiva informa
`MSVC CRT: unwind de dos marcos OK`.

Un segundo punto de prueba provoca un `#UD` dentro de un prologo, despues
de guardar registros y antes de reservar la pila y establecer RBP. El
recorrido aplica solo las operaciones que ya se ejecutaron. Comprueba
RBP, RSI, RDI, RIP y RSP. Con la misma pila de prueba proyecta tres
estados de salida y lee el codigo de cada uno. Comprueba
`add rsp,40`, `lea rsp,[rbp+8]`, la cola `pop rsi; ret` y una
salida indirecta por `jmp [rip+disp32]`. Las cuatro variantes se
detectan en el recorrido Win64 del banco y reconstruyen el mismo
llamador. El puntero del salto debe estar en datos de solo lectura
y resolver a otra funcion del modulo. Un ajuste fuera de la pagina
de pila y una secuencia incompleta dejan intacto el contexto.
La excepcion del CPU ocurre en el prologo.
[Reglas de prologo y epilogo Win64](https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog?view=msvc-170).

La captura cubre `CONTEXT_FULL` de este banco. Quedan pendientes el
estado extendido XSAVE, el despacho SEH general, las excepciones C++
y la inicializacion de la cookie por proceso.

### Filtro SEH compilado por MSVC

El cliente llama a la funcion hoja que provoca `#UD` desde un bloque
`__try`. El recorrido recupera el llamador inmediato. El
`__C_specific_handler` de BMO-X2 para este banco lee la entrada de
alcance emitida por MSVC, comprueba sus RVA e invoca el filtro
compilado con `EXCEPTION_POINTERS`. El filtro coteja el codigo de
excepcion, RIP y RAX. Si acepta, la entrada en Ring 3 ajusta RSP y
transfiere el control al bloque `__except` de ese marco. Si devuelve
`EXCEPTION_CONTINUE_SEARCH`, el control del banco confirma que el
bloque `__except` queda sin ejecutar. En el caso con dos marcos, el
filtro interno declina, el banco desenrolla su marco y el filtro externo
recibe el contexto original del fallo. Se restaura la pila y el estado no
volatil del marco que acepta. Solo se ejecuta el `__except` externo.
Una variante sustituye el filtro interno por un `__finally` compilado
por MSVC. El banco primero selecciona el `__except` exterior. Luego
llama al codigo de limpieza del marco interno con `EXCEPTION_UNWINDING`.
Comprueba `AbnormalTermination()` y el orden exacto de filtro,
`__finally` y `__except`. El objeto del despachador se compila con
`/O1` para respetar el limite del lector FAT32. Este SBEF ocupa 16 466
de los 16 512 bytes permitidos por el banco.

La busqueda general y el desenrollado con destructores de C++ siguen
pendientes. El banco de C++ puede usar su propio cliente SBEF.
[Sintaxis de manejadores SEH de Microsoft](https://learn.microsoft.com/en-us/windows/win32/debug/exception-handler-syntax).
[Evidencia en QEMU](../../Reports/host-msvc-crt-gs-native-qemu.json).
[Formato de excepciones x64 de Microsoft](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170).

`UnwindInventory` registra el numero de funciones de `.pdata`, las
versiones de `UNWIND_INFO`, los manejadores v1 por RVA y los registros
encadenados v1. El informe no ejecuta operaciones de unwind ni despacha
manejadores. Las versiones distintas de v1 se cuentan por su cabecera.
[Formato x64 de Microsoft](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170).

`--msvc-tls` construye un PE32+ freestanding con un `thread_local`
inicializado por MSVC. El banco usa `/Zc:tlsGuards-` para este objeto
estatico sin inicializadores dinamicos. HOST empaqueta dos copias de
la plantilla y rechaza un callback. QEMU verifica dos hilos, un control
con el almacenamiento compartido y la restauracion de la base GS.
[Opcion de MSVC](https://learn.microsoft.com/en-us/cpp/build/reference/zc-tlsguards?view=msvc-170).

```powershell
$validatorRun = 'build/CASM/run-del-validador'
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-tls
```

[Evidencia TLS](../../Reports/host-msvc-tls-qemu.json).

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
bytes desde un PE de 3072 bytes. El paquete paso `inspect`.
[Evidencia HOST](../../Reports/msvc-rebase-intake.json).

La sonda CASM post-EBS de QEMU vuelve a empaquetar ese mismo PE con
SBEF v2 y carga las cuatro regiones desde FAT32. El bucle original de
MSVC lee el puntero reubicado y actualiza el contador en CPL3. El control
con el puntero anterior falla al leer `0x140003000`. Ambos casos limpian
las paginas y restauran el mapa. La sonda LLVM del escritorio sigue
limitada a sus perfiles de direcciones fijas.
[Evidencia QEMU](../../Reports/host-msvc-rebase-qemu.json).

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

Con el PE del informe HOST y un `validator.module.json` auditado en un
run de `build/CASM`, ejecutar la sonda QEMU desde la raiz del repositorio.
La prueba exige la huella exacta del PE archivado para observar el bucle
original con direcciones conocidas.

```powershell
$validatorRun = 'build/CASM/run-del-validador'
python -B tools/boot/sbef_ring0_qemu.py $validatorRun --msvc-rebase build/msvc-intake/rebase/rebase.exe
```

El ejecutable estandar `/MD /EHsc` sigue rechazado. Su informe actualizado
conserva diez modulos y sesenta simbolos, e identifica imports de CRT/Win32,
load config e IAT en [msvc-standard-intake.json](../../Reports/msvc-standard-intake.json).
`probe` tambien detalla `LoadConfigInventory` cuando el PE declara ese
directorio. Informa la VA y RVA de la cookie, si los ocho bytes caben en una
seccion escribible sin ejecucion, los flags CFG reconocidos y los campos de
tabla presentes. El inventario no inicializa la cookie ni aplica CFG.
[Formato PE de Microsoft](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).
El siguiente tramo es llevar el cargador de varias regiones al gestor de
procesos y definir un mapa versionado de servicios para imports. UCRT, VCRUNTIME,
MSVCP y Win32 se habilitaran uno a uno con semantica y pruebas propias.
Luego vendran TLS, unwind y procesos externos. Win32 GUI, DXGI y Direct3D
siguen siendo trabajo posterior; el intake PE no implementa esas APIs.

El siguiente ensayo debe ampliar la tabla de servicios y comprobar
que cada importacion admitida conserva su semantica. El paso grafico
siguiente es un ejemplo
pequeno con DXGI/D3D12, un ejecutor CPU y una superficie de DIRECTOR.
Para darlo por valido en QEMU se comprueba el cuadro y la finalizacion
de la cola. Vulkan y el emisor SM86 tienen pruebas propias de backend.
