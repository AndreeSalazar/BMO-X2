# Motor RmlUi: compilacion nativa x86-64

Ya se compilan RmlUi 6.3, FreeType 2.14.3 y libc++/libc++abi 19.1.7
como objetos ELF64 x86-64 con Clang. No se convierte la DLL Windows.
Esta ruta esta aislada de la prueba HOST y no modifica Ring 0.

**Estado: bibliotecas, no ejecutable.** No hay todavia un SBEF del motor
completo ni una nueva prueba QEMU/METAL. El dibujador Rust previamente
probado en CPL3 sigue siendo una evidencia separada.

## Reproducir

Desde BMO-X2, con Python 3.12+, Git, CMake, tar, LLVM y NMake instalado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\fetch.ps1
python .\tools\desktop\rmlui\native\fetch.py
python .\tools\desktop\rmlui\native\test_inputs.py
python .\tools\desktop\rmlui\native\build.py
Get-Content .\build\rmlui-native\native-results.json
Get-Content .\build\rmlui-native\unresolved.txt
```

NMake solo ejecuta el build: los compiladores son clang/clang++, destino
`x86_64-unknown-none-elf`. No se enlaza MSVC, Windows SDK ni una biblioteca
Linux. `fetch.py` descarga archivos oficiales fijados por SHA256 y extrae
solo bajo `build/deps`. `fetch.py --check` comprueba ademas cada archivo
extraido contra el archivo fijado y las revisiones limpias de RmlUi/FreeType.
No instala nada globalmente. Los archivos se conservan para reproducir y
validar las fuentes; `build/` permanece fuera de Git.

Se usan declaraciones/tipos C de musl 1.2.5, aun sin enlazar su libc.
El encabezado generado de numeros de syscall esta vacio deliberadamente:
no anuncia futex ni una ABI Linux. Los tipos POSIX y la declaracion
`clock_gettime` tampoco implementan servicios del kernel.

El perfil desactiva excepciones, RTTI de C++, hilos, filesystem de libc++,
localizacion, wchar y dispositivo aleatorio. Conserva reloj monotono como
dependencia explicita. No representa toda la biblioteca estandar C++.
En una copia de build de `StringUtilities.cpp` se omite un include
`sstream` que RmlUi no usa; la fuente fijada permanece intacta. La copia
solo cambia ese include y la resolucion de sus dos includes relativos.
Este ajuste esta registrado en `CMakeLists.txt`, no escondido en el cache.

## Resultado medido

En este build con Clang 23.1.2:

| Biblioteca | Objetos ELF64 | Bytes de archivo .a |
| --- | ---: | ---: |
| RmlUi Core | 191 | 6,485,756 |
| FreeType | 42 | 1,104,148 |
| libc++ con libc++abi incorporada | 49 | 914,792 |

El enlace relocatable de los 282 objetos produce 6,726,928 bytes.
Incluye todas las unidades, simbolos y relocaciones; **no mide RAM, SBEF
final ni peso del nano-core**. La seleccion de secciones del enlace final
puede descartar codigo no usado. No prometer una reduccion antes de medirla.

`audit.py` valida los miembros de cada archivo: solo ELF64 little-endian,
ET_REL y maquina 62. Rechaza COFF/Windows, bitcode, otra CPU, truncamientos,
importaciones Windows, unwinder, TLS y pthread pendientes. Enlaza las
bibliotecas de verdad y extrae simbolos sin resolver. El HOST SBEF debe
rechazar este ET_REL con `ELF-HEADER`, campo `e_type`, offset 16.

## Lo que falta para ejecutarlo en Ring 3

El inventario actual tiene 70 simbolos sin resolver, incluidos dos
marcadores de seccion que el enlazador final debe producir. No equivalen
a 70 syscalls ni todos se conservaran tras seleccionar secciones.

1. Memoria acotada: malloc/free/realloc/calloc, alineacion, strings y
   memoria C. Medir heap maximo y fallo de asignacion; no ocultar OOM.
2. Texto y matematicas correctas: conversiones de numeros, formato con
   flotantes, trigonometria, ordenacion y setjmp/longjmp de FreeType.
   El formateador entero usado por DOOM no sustituye estas funciones.
3. Tiempo y entorno: reloj inyectado por el cliente Ring 3; registro y
   cierre. RmlUi recibe fuentes/RML/RCSS por MemoryFiles. Las funciones
   de archivo por defecto deben quedar fuera del enlace o denegar acceso
   explicitamente; no abrir el disco por un fallback silencioso.
4. Entrada y arranque C++: constructores/destructores, errores sin
   excepciones, integracion con DIRECTOR, eventos y VM ULTRA-J nativa.
   El adaptador HOST actual usa try/catch y no se reutiliza sin adaptar.
5. ELF ejecutable sin simbolos pendientes, SBEF admitido, presupuestos
   RX/R/RW/pila y heap medidos, y prueba QEMU de cuadros, entrada,
   cierre, recursos ausentes y rechazo W+X antes de desplegar en METAL.

Hay un cargador de aplicaciones grandes usado por DOOM, separado del
perfil de 16 KiB. Todavia no se selecciona ni se amplian sus limites
para RmlUi: hay que medir el ejecutable real primero.

## Apariencia y responsabilidades

RML estructura los paneles; RCSS define estilo y animacion; ULTRA-J
atiende acciones; DIRECTOR posee foco, ventanas y atajos; Rust dibuja
en CPU y presenta por capacidades. Todo ese trabajo pertenece a Ring 3.
El HOST construye y valida; Ring 0 conserva su frontera privilegiada.

Compilar el Core completo no habilita todos los efectos del backend.
El renderer actual rechaza transformaciones, capas, mascaras y filtros
fuera de su perfil. RmlUi tampoco es un navegador con HTML/CSS/JS completos.
La forma visual puede reutilizar estilo web sin meter un navegador o
un compilador C++ en Ring 0.

Licencias de las fuentes descargadas: LLVM `LICENSE.TXT` (Apache-2.0 con
excepciones LLVM), musl `COPYRIGHT` (MIT y avisos por archivo), RmlUi
`LICENSE.txt` y FreeType `LICENSE.TXT`/`docs/FTL.TXT`. Deben conservarse
los avisos que correspondan cuando se distribuyan binarios enlazados.
