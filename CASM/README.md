# CASM de BMO-X2 (emisor propio, perfiles x86-64)

Esta copia de CASM pertenece al arbol de BMO-X2. Sus perfiles, bytes y contratos
se definen aqui; no se heredan del kernel de ULTRA-LinuX. El compilador actual
se ejecuta en el HOST y esta escrito en C11: GCC o Clang pueden construir esa
herramienta, pero el emisor propio decide los bytes x86-64 del perfil elegido.
Que el compilador HOST use C no convierte en C el codigo emitido para Ring 0.

**Perfiles explicitos:** **metal64 0.2** acepta CASM con un frontend implementado
en C, IR acotada, codificador x86-64 propio, verificador separado y paquete
FAGRAW64 para el puente EFI. **[CASM Native 0.1](native/README.md)** esta escrito en CASM y se autocompila
en Linux x86-64 con funciones, bucles y buffers comprobados. Esa evidencia
corresponde al perfil Native en Linux; no demuestra autocompilacion dentro de
BMO-X2 ni un cargador general de procesos Ring 0. La ampliacion Native no declara
autocompilado el frontend C de metal64.

La definicion del lenguaje esta en [LANGUAGE.md](LANGUAGE.md); el estado real de
cada perfil para BMO-X2 esta en [STATUS-BMO-X2.md](STATUS-BMO-X2.md), y el rumbo
del emisor en [SAMURAI.md](SAMURAI.md).

## Origen

Copiado de [TALK-CPU-x86-64](https://github.com/AndreeSalazar/TALK-CPU-x86-64), commit
`b5b8e88`, del mismo autor; las huellas de abajo son las del origen. Desde la 0.2 el
lenguaje crece aqui. No se modifico ni se envio nada a ese repositorio.

| Archivo | SHA-256 en el origen |
|---|---|
| src/casm.h | 07cb3fa40ab6baa0dcfd590b7180c85a3f3c1d618a868353c936d6be99677302 |
| src/frontend.c | 7ded0c98400b1e411644526971cc4df31f9238c566fb378be11c57c28bf4d2e2 |
| src/emitter.c | 416c2cfaf0f2c68a45def3656a4872308fc4ac69b883f5dd69ff04f2dcb95ea6 |
| src/main.c | 47dc776884a682cac3e4ffc259cbb25bd25faec93be2680ca401a3ee287796a1 |
| verify.py | 1b9eb76530dfacdeb57f84b3755c810c17201b9a97ec701e56ed67ed08b5966e |
| LANGUAGE.md | 01be4029a26fa05c5f0009a9bf8d952e5af6800d3ed53b3bfcc6fcc295193b94 |
| examples/hello.casm | 63bb72f6eaa4722b7f91133ab8b7635d1e55290d276673ca42ebf2bc26711547 |

`test.py` cambia el compilador a `build/CASM/host/casmc` (Linux) en vez de `casmc.exe`,
y aqui crecio: cada katana tiene su caso aislado y cada caso exige SU regla. Desde la
0.2, CASM tiene enteros exactos (`frontend.c`, `emitter.c` y `verify.py` ampliados; ver
[SAMURAI.md](SAMURAI.md)). Los scripts de PowerShell y la prueba QEMU del puente no se copiaron.

## Aislado

- **Semilla GCC o Clang para el HOST.** El compilador sigue escrito en C. `construir.sh`
  acepta `--compilador gcc|clang`, conserva los avisos como errores y el
  endurecimiento; GCC añade `-fanalyzer`. Guarda version, banderas y huellas en
  `toolchain.txt` y `toolchain.json`. El codificador de CASM no usa el backend de
  GCC/LLVM para emitir el programa.
- **Uso sin GCC/Clang:** una semilla vigente se reutiliza comprobando las huellas
  de sus fuentes y ejecutable. `compilar.sh` ya no la reconstruye en cada uso.
  Si falta o cambia, necesita nuevamente una semilla externa. **Todavia no es
  autocompilacion:** el camino verificable esta en [AUTOCOMPILACION.md](AUTOCOMPILACION.md).
- **Destino x86-64.** `metal64` es un perfil propio de emision; el adaptador
  opcional **Linux ELF** es otro entorno de ejecucion de CASM 0.2, sin ensamblador
  ni enlazador externo. No es el ABI SysV general ni libc, y no es el destino Ring 0.
- **Sin dependencias externas:** C11 con la libc y Python 3 con su biblioteca estandar.
- **Solo escribe en `build/CASM/`** (ignorado por git). No toca discos, entradas de
  arranque ni paquetes instalados.

## Uso

Los comandos Linux de esta seccion usan Linux como HOST de construccion y prueba.
No implican que BMO-X2 arranque Linux. Ejecutar desde una copia editable del
proyecto, por ejemplo en `~/Proyectos`; una copia montada en solo lectura no
puede escribir `build/CASM`.

```bash
CASM/probar.sh                      # 108 casos (61 katanas) + paquete de oro (identico al .hex a mano)
CASM/compilar.sh                    # examples/hello.casm -> build/CASM/run-*/INICIO.X86
CASM/compilar.sh CASM/examples/enteros.casm   # CASM 0.2: enteros exactos
CASM/compilar.sh mi-programa.casm
bash CASM/compilar-native.sh CASM/native/ejemplo.casm  # perfil Linux autocompilado
CASM/construir.sh --compilador clang # semilla alternativa, sin GCC
CASM/compilar.sh --linux            # tambien program.elf, .linux.hex y .linux.json
python3 CASM/contrastar.py          # semillas, sanitizadores, comparacion byte a byte
python3 CASM/probar_elf_linux.py    # ejecutar dentro del taller Linux x86-64
python3 CASM/probar_bootstrap.py    # invalidacion de huellas y perfiles
```

Cada compilacion deja en `build/CASM/run-*` la fuente congelada, el HEX, la IR, el
paquete (solo si se verifico), `verified.json`, `registro.txt` (lo que dijeron el
compilador y el verificador), `origen.txt` y `toolchain.txt`. El panel **Taller CASM**
de ULTRA Carpetas lo lee todo.

Comprobado aqui con GCC 13.3: 108/108 casos, y `hello.x86` con SHA-256
`b3fd9814bcce6881f9cf3ad10b299d759f4f5b801a6526c59131a4d1c84e4b33`, el mismo que las
evidencias de TALK-CPU para el `.hex` escrito a mano.

La validacion GCC/Clang y el destino Linux actuales se documentan en
[AUTOCOMPILACION.md](AUTOCOMPILACION.md). Las banderas de diagnostico solo se usan
en variantes de laboratorio, separadas de `host`.
