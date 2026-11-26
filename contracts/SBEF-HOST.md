# SBEF x86-64 en HOST

La estructura del [HOST](../tools/host/README.md) separa importadores,
formato SBEF, diagnosticos y banco de toolchains. Los comandos de este
contrato conservan sus puntos de entrada.

El registro ejecutable `python -B tools/sbef.py profiles` distingue productor,
formato, destino x86-64, admision y evidencia de ejecucion. MSVC PE y
LLVM/GCC/Rust ELF reutilizan lectores de formato cuando corresponde; la
procedencia debe adjuntarse al informe de build y no se infiere del ejecutable.
Un perfil admitido por HOST no equivale a un proceso cargable: el cargador
Ring 3 y sus servicios tienen evidencia independiente.

`tools/sbef.py pack` toma un ELF64 x86-64 estatico y enlazado,
extrae los segmentos PT_LOAD y construye un SBEF. `inspect` comprueba
el contenedor resultante desde sus bytes. El mismo paso puede consumir
la salida enlazada de C, C++ o Rust. Cada productor aporta su inicio
`_start` y sus dependencias de runtime. El ABI 0 reserva la prueba
freestanding con inicio explicito, sin TLS, constructores automaticos
ni desenrollado de pila. SBEF sigue sujeto a las puertas de admision, pero
el perfil ISA y su representacion en el encabezado quedan fijados aqui.

```powershell
$llvm = Join-Path $env:ProgramFiles 'LLVM/bin'
& "$llvm/clang.exe" --target=x86_64-unknown-none-elf -ffreestanding -fno-pic -fno-pie -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables -O2 -c app.c -o app.o
& "$llvm/ld.lld.exe" -static -T userspace/sbef.ld app.o -o app.elf
python -B tools/sbef.py pack app.elf app.sbef
python -B tools/sbef.py pack app.elf app-v2.sbef --isa-profile x86-64-v2
python -B tools/sbef.py pack app.elf app-legacy.sbef --format-version 1
python -B tools/sbef.py pack app.elf app-abi1.sbef --abi 1
python -B tools/sbef.py --json-errors pack app.elf app-limited.sbef --abi 1 --max-file-bytes 512 --max-mapped-bytes 8192
python -B tools/sbef.py inspect app.sbef
python -B tools/sbef.py plan app.sbef
python -B tools/sbef.py compare baseline.sbef candidate.sbef
python -B tools/sbef.py probe app.elf
python -B tools/sbef.py probe app.exe
```

Ejecutar los comandos desde la raiz de BMO-X2. En C++ declarar
`extern "C"` para `_start` y construir con `-fno-exceptions -fno-rtti`
para este perfil minimo. Rust necesita un target x86-64 freestanding,
`no_std`, inicio propio y panic abort. Sus bibliotecas deben estar
compiladas para el mismo target y contrato. La prueba HOST construyo
ejemplos C y C++ con Clang y LLD, ambos de 112 bytes. El escritorio
Rust usa el target `x86_64-unknown-none` y ya arranca desde SBEF.

Ejemplo minimo para reproducir el empaquetado en C:

```c
static volatile unsigned counter = 1;

void _start(void) {
    counter = counter + 1;
    __builtin_trap();
}
```

El ejemplo usa una trampa como final de la prueba de build. La salida
ordenada del proceso se definira en el ABI de Ring 3.

`probe` muestra si la entrada ELF64 cumple el perfil y que regiones
tendria su SBEF. Para PE32+ muestra el punto de entrada, las secciones,
los permisos y directorios relevantes como importaciones, TLS y
reubicaciones. `pack --abi 1` admite los perfiles PE freestanding fijos
RX y RX/R/RW y un perfil PE32+ EXE de consola limitado. Este ultimo puede
mapear hasta ocho secciones ordenadas, sin W+X, y aplicar solo
relocaciones DIR64 a direcciones internas mapeadas. Requiere DYNAMIC_BASE
si cambia la base. Rechaza imports/IAT, DLL, TLS, load config, unwind y
directorios que aun no tienen contrato de ejecucion. Vease el alcance y
la evidencia MSVC en [HOST](../tools/host/README.md).
`--json-errors` antes de la accion devuelve por
stderr codigo, campo y offset de archivo, con indice de region
cuando corresponde. El archivo se escribe solo despues de admitirlo.

### EXE con una DLL fija

`pack --abi 1 --with-dll module.dll` selecciona `win64-fixed-dll-v1`.
HOST admite un EXE de consola de tres regiones y una DLL de base fija
con una exportacion directa por nombre. Ambos se enlazan por separado.
HOST exige que la importacion del EXE corresponda al nombre de la DLL y
que la exportacion apunte a bytes RX del modulo. Escribe la direccion en
la IAT de solo lectura del EXE y conserva las regiones del modulo en el
mismo SBEF v2. El informe incluye el hash y la exportacion de la DLL.
El perfil exige una DLL sin punto de entrada ni dependencias y rechaza
reenvios, TLS y directorios de ejecucion ajenos al perfil. Quedan
pendientes carga dinamica, inicializacion y cierre de DLL, el CRT y el
soporte de excepciones. [Pruebas HOST y QEMU](../Reports/host-msvc-dll-qemu.json).

### Perfil ISA

El destino x86-64 de BMO-X2 tiene una base `x86-64-v1` y cuatro niveles
declarables. Cada nivel suma requisitos al anterior:

| Nivel | Requisitos agregados |
|---|---|
| `x86-64-v1` | CMOV, CX8, FPU, FXSR, MMX, SCE, SSE, SSE2 y estado OSFXSR habilitado |
| `x86-64-v2` | CMPXCHG16B, LAHF-SAHF, POPCNT, SSE3, SSE4.1, SSE4.2, SSSE3 |
| `x86-64-v3` | AVX, AVX2, BMI1, BMI2, F16C, FMA, LZCNT, MOVBE, OSXSAVE y XCR0 para AVX |
| `x86-64-v4` | AVX512F, AVX512BW, AVX512CD, AVX512DQ, AVX512VL y XCR0 para ZMM |

La tabla sigue los niveles de microarquitectura del [x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI/blob/master/x86-64-ABI/low-level-sys-info.tex).
El campo SBEF declara el minimo requerido; no es una auditoria de opcodes.
El HOST no desensambla ni corrige automaticamente instrucciones por encima
del nivel declarado. El codigo de las sondas LLVM consulta CPU y estado; falta
compilarlo y validarlo en QEMU. La comprobacion CASM del cargador general aun
depende de cerrar la puerta 1.

Los limites opcionales de `pack` miden el archivo SBEF completo y la
suma de paginas de sus regiones. Incluyen el BSS en el presupuesto
mapeado. Pila, tablas y recursos externos tienen cuentas propias.
Un exceso informa `SBEF-BUDGET` con bytes reales y limite, y conserva
el archivo de salida anterior.

`compare` valida los dos archivos y exige la misma version de ABI.
Muestra el tamano de cada SBEF y el total mapeado, con el delta
candidato menos base. Identifica regiones por direccion y permisos y
desglosa sus bytes de archivo, memoria y paginas. Un cambio de direccion
o permisos aparece como una region retirada y otra agregada.

`plan` vuelve a validar el SBEF y emite el mapa de paginas de usuario que
el cargador deberia construir: rangos, permisos, bytes copiados y puestos
a cero, y ubicacion de entrada. Es la salida de referencia HOST para la
implementacion CASM; no ejecuta el archivo ni sustituye la asignacion de
pila y la gestion de vida del proceso.

El importador copia los bytes de segmentos PT_LOAD. Los metadatos y
simbolos fuera de esos segmentos quedan en el ELF para diagnostico.
El enlazador decide el contenido de cada segmento. El importador
preserva esos bytes para mantener el comportamiento de la aplicacion.

## Contrato binario provisional

Cabecera de 32 bytes little-endian. Le siguen de una a ocho entradas
de 32 bytes y el contenido de los segmentos concatenado.

| Offset | Campo | Tipo |
|---:|---|---|
| 0 | Firma ASCII SBEF | 4 bytes |
| 4 | Version de formato, 1 heredada o 2 actual | u16 |
| 6 | Version de ABI (0 de build, 1 candidato de llamadas) | u16 |
| 8 | Arquitectura x86-64, 62 | u16 |
| 10 | Cantidad de regiones | u16 |
| 12 | Tamano del archivo | u32 |
| 16 | Punto de entrada virtual | u64 |
| 24 | v1: flags cero; v2: identificador ISA | u32 |
| 28 | Reservado cero | u32 |

En formato 2, el identificador ISA en el offset 24 es: 1=`x86-64-v1`,
2=`x86-64-v2`, 3=`x86-64-v3`, 4=`x86-64-v4`. Otros valores se rechazan.
En formato 1, el campo debe ser cero y el paquete se interpreta como
`x86-64-v1`, manteniendo compatibilidad con paquetes heredados. La version
del ABI permanece independiente de la version del formato y del perfil ISA.
SBEF mantiene arquitectura ELF 62 (x86-64); no admite otra ISA.

Cada region usa direccion virtual u64, offset de archivo u32, bytes
de archivo u32, bytes en memoria u32, permisos u32 y reservado u64 a
cero. Los permisos admitidos son R=4, RX=5 y RW=6; el cargador debe
activar NX donde falte X. La entrada debe apuntar a bytes de archivo
en una region RX. Las paginas se alinean a 4 KiB y el tramo posterior
a los bytes de archivo se inicializa a cero. El prototipo usa la ventana
`[0x40000000, 0x41000000)` y un maximo de 1 MiB por archivo.

El lector HOST rechaza cabeceras truncadas, permisos W+X, rangos fuera
de la ventana, solapes virtuales a nivel de pagina, huecos en el archivo
y puntos de entrada fuera de codigo. El [ensayo ABI 1](../kernel/syscalls/ABI-PROBE.md)
arranca una imagen embebida fija y verifica dos rechazos. Queda probar
una imagen externa producida por los toolchains.
