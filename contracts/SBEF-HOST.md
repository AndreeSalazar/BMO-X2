# SBEF provisional en HOST

`tools/sbef.py pack` toma un ELF64 x86-64 estatico y enlazado,
extrae los segmentos PT_LOAD y construye un SBEF. `inspect` comprueba
el contenedor resultante desde sus bytes. El mismo paso puede consumir
la salida enlazada de C, C++ o Rust. Cada productor aporta su inicio
`_start` y sus dependencias de runtime. El ABI 0 reserva la prueba
freestanding con inicio explicito, sin TLS, constructores automaticos
ni desenrollado de pila. El formato y el ABI son provisionales.

```powershell
$llvm = Join-Path $env:ProgramFiles 'LLVM/bin'
& "$llvm/clang.exe" --target=x86_64-unknown-none-elf -ffreestanding -fno-pic -fno-pie -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables -O2 -c app.c -o app.o
& "$llvm/ld.lld.exe" -static -T userspace/sbef.ld app.o -o app.elf
python -B tools/sbef.py pack app.elf app.sbef
python -B tools/sbef.py inspect app.sbef
```

Ejecutar los comandos desde la raiz de BMO-X2. En C++ declarar
`extern "C"` para `_start` y construir con `-fno-exceptions -fno-rtti`
para este perfil minimo. Rust necesita un target x86-64 freestanding,
`no_std`, inicio propio y panic abort. Sus bibliotecas deben estar
compiladas para el mismo target y contrato. La prueba HOST construyo
ejemplos C y C++ con Clang y LLD, ambos de 112 bytes. Este anfitrion
tiene Rust para Windows y WASM, y queda por probar el target ELF.

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

## Contrato binario provisional

Cabecera de 32 bytes little-endian. Le siguen de una a ocho entradas
de 32 bytes y el contenido de los segmentos concatenado.

| Offset | Campo | Tipo |
|---:|---|---|
| 0 | Firma ASCII SBEF | 4 bytes |
| 4 | Version de formato 1 | u16 |
| 6 | Version provisional de ABI 0 | u16 |
| 8 | Arquitectura x86-64, 62 | u16 |
| 10 | Cantidad de regiones | u16 |
| 12 | Tamano del archivo | u32 |
| 16 | Punto de entrada virtual | u64 |
| 24 | Flags y reservado, ambos cero | 2 x u32 |

Cada region usa direccion virtual u64, offset de archivo u32, bytes
de archivo u32, bytes en memoria u32, permisos u32 y reservado u64 a
cero. Los permisos admitidos son R=4, RX=5 y RW=6; el cargador debe
activar NX donde falte X. La entrada debe apuntar a bytes de archivo
en una region RX. Las paginas se alinean a 4 KiB y el tramo posterior
a los bytes de archivo se inicializa a cero. El prototipo usa la ventana
`[0x40000000, 0x41000000)` y un maximo de 1 MiB por archivo.

El lector HOST rechaza cabeceras truncadas, permisos W+X, rangos fuera
de la ventana, solapes virtuales a nivel de pagina, huecos en el archivo
y puntos de entrada fuera de codigo. La proxima prueba debe producir
los mismos rechazos y arrancar una imagen aceptada desde el cargador CASM.
