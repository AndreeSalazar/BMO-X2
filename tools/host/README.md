# HOST de BMO-X2

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
| `toolchains/abi.py` | Compilar un cliente ABI comun con GCC o Clang y cotejar el portal con el vector HEX. Inventariar el objeto COFF de MSVC. |
| `importers/elf.py` | Validar ELF64 estatico y extraer los segmentos cargables. |
| `importers/pe.py` | Inventariar PE32+ y explicar sus bloqueos de admision. |
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
de Microsoft x64 al contrato INVOKE/WAIT. El binario requiere la ABI de
BMO-X2. El perfil de importacion PE queda pendiente: HOST informa
`.pdata`, permisos de seccion y dependencias antes de admitir un PE.
Las APIs Win32, DLL, TLS y el runtime de C/C++ exigen servicios
adicionales en Ring 3.
