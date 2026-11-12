# DOOM en BMO-X2

BMO-X compilo DoomGeneric con su propio compilador C x86-64 y produjo
`doom.bex` en BEF2. Ese paquete devuelve `ELF-HEADER` en `e_ident`
(offset 0) al pasarlo al importador SBEF. El camino de BMO-X2 parte del
codigo C y enlaza un ELF64 estatico con el portal ABI 1.

## Sonda reproducible en Windows PowerShell 5.1

Desde la raiz de BMO-X2, con LLVM y Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-doom-probe.ps1
```

El script busca DoomGeneric en el BMO-X vecino y verifica la huella de
`m_fixed.c` del commit `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`.
Para otro checkout de ese commit, pasa `-DoomSource` con la ruta a la
carpeta interna `doomgeneric` que contiene `m_fixed.c`.
El argumento `-Gcc` admite la ruta de un GCC cuyo destino sea x86-64 ELF.
La prueba nativa y el enlace siguen usando LLVM. La variante GCC queda
pendiente de verificar.

| Salida en `build/doom-probe` | Resultado observado con Clang |
|---|---|
| `doom-fixed-host.exe` | Cuatro casos de `FixedMul` y `FixedDiv`, incluida saturacion al dividir por cero. |
| `doom-fixed.elf` | 5584 bytes. Un `PT_LOAD` RX de 451 bytes en offset `0x1000`. |
| `elf-segments.txt` | Direccion virtual, permisos, alineacion y tamanos del segmento. |
| `doom-fixed.sbef` | 515 bytes. Cabecera y tabla de 64 bytes, seguidas por el mismo contenido RX del ELF. |

El contenido RX queda en la direccion virtual `0x40000000` y ocupa una
pagina mapeada de 4096 bytes. Esa cifra cubre la region del binario.
La ejecucion del SBEF en QEMU queda pendiente.

## Del escritorio al primer cuadro de DOOM

1. Cargar el SBEF externo en QEMU y comprobar el portal ABI desde CPL3.
2. Presentar el framebuffer del escritorio Rust y entregar eventos de
   teclado al espacio activo. Probar los cuatro atajos Super + numero.
3. Adaptar las funciones DoomGeneric de dibujo, teclado y reloj a esos
   servicios. Dar al juego memoria de trabajo y lectura de un WAD externo.
4. Compilar el motor completo en C, enlazarlo como ELF64 y empaquetarlo.
   Verificar en QEMU la lectura del WAD y un cuadro que responda al teclado.
   El sonido puede integrarse despues.

[Fuente DoomGeneric fijada](https://github.com/ozkl/doomgeneric/tree/dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284) |
[Cargador SBEF](../../../contracts/SBEF-LOADER.md) |
[Escritorio](../../services/desktop/WORKSPACES.md)
