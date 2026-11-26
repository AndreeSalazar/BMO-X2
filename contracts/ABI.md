# ABI 1 de BMO-X2, candidato

El campo ABI del SBEF selecciona el contrato del proceso. La version
1 usa dos numeros de puerta propios sobre SYSCALL x86-64. INVOKE
recibe una capacidad del proceso y una operacion sobre ella. WAIT
recibe un objeto esperable, su secuencia observada y un plazo.

| Registro | INVOKE (0) | WAIT (1) |
|---|---|---|
| RAX | 0 | 1 |
| RDI | Capacidad | Capacidad |
| RSI | Operacion | Secuencia observada |
| RDX | Argumento 0 | Plazo monotono en ns |
| R10 | Argumento 1 | Cero |
| R8 | Argumento 2 | Cero |
| R9 | Cero | Cero |

RAX devuelve estado firmado y RDX un valor de 64 bits. RDX queda
a cero en errores. RCX y R11 quedan volatiles. El kernel cambia a
una pila de confianza antes de guardar el marco y devuelve por
IRETQ en este perfil. El cliente ELF recibe RSP alineado a 16 en
la entrada. Su stub `_start` llama a `bmo_main` con la convencion
de funciones del toolchain. El perfil externo devuelve RFLAGS con IF
activo para el temporizador. La politica del proceso real queda pendiente.

| Estado | Significado |
|---:|---|
| 0 | Operacion completada |
| -1 | Numero de puerta desconocido |
| -2 | Capacidad invalida |
| -3 | Argumentos invalidos |
| -4 | Mecanismo pendiente |
| -5 | Operacion desconocida |
| -6 | Plazo vencido |

El primer INVOKE usa la capacidad de prueba 1 y operacion ECHO 1.
Devuelve el argumento 0 sin copiar memoria de usuario. La sonda ABI
embebida conserva el recibo -4 para WAIT.

El perfil QEMU con SBEF externo desde FAT32 usa el portal SysV y ejecuta
INVOKE y WAIT mediante SYSCALL. La puerta toma una pila de supervisor,
valida el RSP y la direccion de retorno e instala un marco IRETQ. El
despacho comprueba ECHO, capacidad, operacion, numero de llamada y
argumentos reservados. La prueba fuerza RSP cero y el kernel termina
la sesion sin usar esa pila.
La limpieza restaura y relee EFER, STAR, LSTAR y FMASK. El cierre usa la
puerta de prueba. El perfil `--external` ejecuta un solo proceso.
[Evidencia del ABI externo](../Reports/casm-sbef-external-abi-qemu.json).

La capacidad de prueba 2 del perfil externo publica una secuencia con
INVOKE 1 y lee el reloj monotono con INVOKE 2. Ambas operaciones exigen
argumentos cero. El reloj empieza en cero al armar el PIT y avanza
10 000 150 ns por interrupcion. WAIT comprueba la capacidad y devuelve
la secuencia nueva con estado 0 si difiere de la observada, incluso con
plazo vencido. Con secuencia igual, devuelve -6 al alcanzar el plazo
absoluto y -3 si faltan mas de 1 000 000 000 ns. Mientras espera, ejecuta
`STI`, `HLT` y `CLI` y vuelve a comprobar la condicion. La prueba mide
los despertares y comprueba la expiracion y la senal ya publicada.
El PIT y el PIC se configuran para esta VM desechable.
[Evidencia de WAIT](../Reports/casm-sbef-external-wait-qemu.json).

El perfil `--peer` prueba dos contextos CPL3 sobre una sola CPU virtual.
Cada uno tiene su propio CR3 y su propia pila. Comparten la primera
pagina RX del SBEF. El cliente usa la capacidad 2 para esperar y leer el
reloj. Un segundo contexto, con la capacidad 3, publica la secuencia
mediante INVOKE 1 y devuelve el control al cliente suspendido. La sonda
verifica que el cliente recibe la secuencia antes del plazo sin esperar
un tick, que conserva su pila y que un intento del emisor de leer la
pagina privada del cliente causa un fallo de pagina. El cambio de
contexto es cooperativo y el emisor termina al publicar. Quedan pendientes
una tabla general de capacidades por proceso, el planificador y una
segunda imagen con admision independiente.
La reserva aumenta siete paginas de 4 KiB para las tablas, la pila de
usuario y la extension de la sonda.
[Evidencia del despertar entre contextos](../Reports/casm-sbef-peer-qemu.json).

## Consola Win64 externa en QEMU

El perfil de prueba `win64-console-v1` expone el reloj de la capacidad 2
y las operaciones de consola de la capacidad 4. INVOKE 1 sobre 4 recibe
de uno a ocho bytes en RDX, en orden little-endian, y la longitud en R10.
Ring 0 escribe los bytes al canal de prueba de QEMU y devuelve su cantidad
en RDX. Valida los argumentos antes de emitir y aplica una cuota de 4096
bytes por sesion. INVOKE 2 sobre 4 cierra el proceso con un codigo de 0 a
255 en RDX y ejecuta la limpieza habitual. R8 y R9 deben estar a cero en
ambas operaciones. R10 debe estar a cero al cerrar.

HOST resuelve `GetTickCount64`, `GetStdHandle` y `WriteFile` contra
adaptadores Rust Win64 de Ring 3. El reloj se convierte a milisegundos y
`WriteFile` admite stdout sincronico. Los punteros del cliente se usan en
Ring 3. La puerta de Ring 0 recibe unicamente palabras y cantidades.
La concesion de capacidades es fija para esta sonda. El perfil no forma
parte de la cabecera SBEF y no cubre errores Win32 completos, DLL, CRT,
archivos ni operaciones asincronas.
[Evidencia de la consola externa](../Reports/host-msvc-console-qemu.json).

## Sonda de entrada del escritorio

El perfil experimental `desktop-external` prueba otra puerta con
`WAIT(entrada, 0, ticks)`. Acepta de 0 a 100 ticks relativos del
PIT de aproximadamente 10 ms. Devuelve 0 cuando hay un byte en
PS/2, 256 al vencer y 257 si rechaza la peticion. INVOKE consume
el byte. Ring 0 consulta el FIFO antes de dormir con `STI; HLT`
y despues de cada interrupcion del PIT. El ensayo verifica HLT,
vencimiento y reanudacion con entrada. Sigue pendiente integrar
esta prueba en CASM, despertar por IRQ de entrada, aplicar la
secuencia y el plazo monotono del contrato, y planificar varios
procesos.

## Extension experimental de diagnostico EP0

Solo la sonda `XHCI_ENUM_PROBE` agrega selectores de lectura a la
capacidad 3, operacion 3. Conserva los selectores 0..7 y los numeros
de puerta. Esta extension de la sonda devuelve la palabra en RAX;
no sustituye el contrato general de resultados descrito arriba.
No admite direcciones proporcionadas por el llamador ni concede MMIO.

| Selector | Palabra devuelta |
|---|---|
| 8 | Dwords de estado y control del ultimo evento, en bits 0..31 y 32..63. |
| 9 | Puntero TRB del evento capturado. |
| 10 | Prefijo de dispositivo de 8 B, little-endian. Requiere reserva DMA validada. |
| 11 | Puerto en bits 0..7, velocidad en 8..15, longitud solicitada en 16..31. |
| 12 | Puntero esperado de terminacion de la operacion actual. |
| 13 | Primeros dos dwords del contexto EP0 de salida: estado y parametros, incluido MPS. |
| 14 | TR Dequeue Pointer de EP0 en el contexto de salida. |
| 15 | TR Dequeue Pointer de EP0 en el contexto de entrada. |
| 16 | Tamano de contexto descubierto: 32 o 64 bytes. |

Sin esa opcion de compilacion los selectores continuan rechazados.
Los selectores 13..16 exigen tambien reserva DMA validada y calculan
sus direcciones a partir de esa reserva y del tamano descubierto.
Los resultados son instantaneas del perfil finito y se leen despues de
parar el controlador. Un evento vacio no acredita terminacion correcta.

## Reproduccion de herramientas

```powershell
.\bmo-x2.ps1 -Accion abi
.\bmo-x2.ps1 -Accion abi -Cpu Nehalem
$llvm = Join-Path $env:ProgramFiles 'LLVM/bin'
python -B tools/abi_toolchain.py clang --cc "$llvm/clang.exe" --ld "$llvm/ld.lld.exe" --objcopy "$llvm/llvm-objcopy.exe"
```

En un entorno con GCC x86-64 ELF y LLVM binutils, ejecutar
`python3 -B tools/abi_toolchain.py gcc`. En una consola de Visual
Studio x64, `python -B tools/abi_toolchain.py msvc` prueba el
encabezado y produce COFF para inventario. Con `--pe-link link.exe`
el cliente enlaza con el portal de [Microsoft x64](../userspace/runtime/abi/win64/portal.rs)
para inspeccion PE. Con `--abi-run`, HOST empaqueta el perfil fijo
como SBEF y prueba el cliente en CPL3. La frontera del kernel conserva
el ABI nativo.

[SBEF HOST](SBEF-HOST.md) | [Ensayo QEMU](../kernel/syscalls/ABI-PROBE.md)
