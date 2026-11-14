# HOST de BMO-X2

HOST recibe un ejecutable x86-64 enlazado y decide si cumple el perfil
de aplicacion. El resultado admitido es un SBEF con un ABI, entrada,
regiones y permisos definidos. El ejecutable mantiene el codigo de
maquina que emitio el compilador.

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

El banco embebe una region RX en el paquete de prueba. Falta repetir
la comparacion con el cargador externo general y un segundo proceso.
El perfil PE32+ freestanding de MSVC queda por implementar. HOST
expone dependencias de DLL, TLS y otros directorios en `probe`.
