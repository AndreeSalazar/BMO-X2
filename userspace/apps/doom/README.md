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
La prueba nativa y el enlace siguen usando LLVM. La prueba de invitado
se verifico con GCC 15.2.0.

| Salida en `build/doom-probe` | Resultado observado con GCC 15.2.0 para ELF |
|---|---|
| `doom-fixed-host.exe` | Cuatro casos de `FixedMul` y `FixedDiv`, incluida saturacion al dividir por cero. |
| `doom-fixed.elf` | Un `PT_LOAD` RX de 452 bytes en offset `0x1000`. |
| `elf-segments.txt` | Direccion virtual, permisos, alineacion y tamanos del segmento. |
| `doom-fixed.sbef` | 516 bytes. Cabecera y tabla de 64 bytes, seguidas por el mismo contenido RX del ELF. |

El contenido RX queda en la direccion virtual `0x40000000` y ocupa una
pagina mapeada de 4096 bytes. Esa cifra cubre la region del binario.

## Prueba de invitado en QEMU

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion abi
$abi = Get-ChildItem .\build\CASM -Directory -Filter 'run-*' |
    Sort-Object LastWriteTime -Descending |
    Where-Object { (Test-Path (Join-Path $_.FullName 'profile.txt')) -and
        (Get-Content (Join-Path $_.FullName 'profile.txt')) -eq 'ring0-abi-probe-0.1' } |
    Select-Object -First 1
$gcc = (Resolve-Path .\build\tools\gcc-15.2.0\bin\x86_64-elf-gcc.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-doom-probe.ps1 -Gcc $gcc -AbiRun $abi.FullName
```

Usa la ruta real de GCC si esta en otra carpeta. El ensayo crea una copia
del perfil ABI verificado y ajusta cinco campos de su vector para admitir
el SBEF de una sola region RX y comprobar su terminal. El paquete de
arranque incorpora el SBEF byte por byte. El monitor coteja el cuerpo
arrancado, tres entradas SYSCALL y el marco de CPL3. La marca final exige
que las cuatro operaciones de DoomGeneric, ECHO, el rechazo de capacidad
y el estado de WAIT hayan pasado. El kernel borra 8192 bytes de usuario.
El run conserva el SBEF, el disco virtual, la captura y el JSON.

El cargador general de SBEF externo y el motor jugable siguen pendientes.

## Del escritorio al primer cuadro de DOOM

1. Cargar el SBEF externo en QEMU y comprobar el portal ABI desde CPL3.
2. Presentar el framebuffer del escritorio Rust y entregar eventos de
   teclado al espacio activo. Probar Ctrl + Super + numero para espacios.
3. Adaptar las funciones DoomGeneric de dibujo, teclado y reloj a esos
   servicios. Dar al juego memoria de trabajo y lectura de un WAD externo.
4. Compilar el motor completo en C, enlazarlo como ELF64 y empaquetarlo.
   Verificar en QEMU la lectura del WAD y un cuadro que responda al teclado.
5. Conectar efectos y musica a fuentes independientes del
   [servicio de audio](../../services/audio/AUDIO.md).

[Fuente DoomGeneric fijada](https://github.com/ozkl/doomgeneric/tree/dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284) |
[Cargador SBEF](../../../contracts/SBEF-LOADER.md) |
[Escritorio](../../services/desktop/WORKSPACES.md)
