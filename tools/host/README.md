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

## Proximas pruebas

1. Ejecutar el mismo cliente ABI de GCC y Clang en Ring 3 y comparar su
   resultado. Las huellas identifican el build de cada productor.
2. Ampliar el banco con clientes C++ y Rust para el mismo ABI. Cada
   perfil debe declarar inicio y runtime propios.
3. Definir y probar un PE32+ freestanding enlazado con MSVC. Los
   binarios Windows con DLL, TLS o requisitos de Win32 necesitan
   contratos adicionales. HOST expone esas dependencias en `probe`.
