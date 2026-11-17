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
de funciones del toolchain. La prueba restaura RFLAGS a 2; queda
pendiente definir la politica de interrupciones del proceso real.

| Estado | Significado |
|---:|---|
| 0 | Operacion completada |
| -1 | Numero de puerta desconocido |
| -2 | Capacidad invalida |
| -3 | Argumentos invalidos |
| -4 | Mecanismo pendiente |
| -5 | Operacion desconocida |

El primer INVOKE usa la capacidad de prueba 1 y operacion ECHO 1.
Devuelve el argumento 0 sin copiar memoria de usuario. WAIT reconoce
el numero 1 y devuelve -4. Su semantica candidata compara la
secuencia y espera un cambio o el plazo; falta implementar el
bloqueo, la senal, el vencimiento y las carreras de ambos.

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
