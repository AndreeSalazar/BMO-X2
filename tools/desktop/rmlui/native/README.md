# Motor RmlUi nativo en Ring 3 x86-64

`guest.py --desktop` agrega la politica de espacios/foco/cierre de
DIRECTOR Rust. `media.py` prueba lectura FAT32 por UEFI y produce el
candidato separado para A:. [Arranque y estado fisico](../../../../docs/NATIVE-DESKTOP-BOOT.md).
El modo sin --desktop conserva el visor independiente descrito abajo.

Ya se compilan RmlUi 6.3, FreeType 2.14.3 y libc++/libc++abi 19.1.7
como objetos ELF64 x86-64 con Clang. No se convierte la DLL Windows.
Esta ruta esta aislada de la prueba HOST. Usa un perfil explicito del
cargador de aplicaciones grandes y de la presentacion por capacidades.

**Estado: ejecutable SBEF probado en CPL3/QEMU.** El Core real carga
RML/RCSS y fuentes desde memoria, dibuja con Rust CPU y ejecuta UJBC con
la VM nativa de ULTRA-J. Enter y clic PS/2 activan el boton. Esc termina
el ensayo y verifica que RmlUi libere geometria, texturas y cursores.
La ventana QEMU conserva el ultimo cuadro hasta cerrarla.

Es un visor independiente, con movimiento reducido. Todavia no sustituye
el escritorio DIRECTOR ni acredita USB fisico o arranque de este motor
en METAL. Navegacion lateral y ajustes son representacion visual.

## Reproducir

Desde BMO-X2, con Python 3.12+, Git, CMake, tar, LLVM y NMake instalado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\fetch.ps1
python .\tools\desktop\rmlui\native\fetch.py
python .\tools\desktop\rmlui\native\test_inputs.py
python .\tools\desktop\rmlui\native\build.py
python .\tools\desktop\rmlui\native\guest.py
Get-Content .\build\rmlui-native\native-results.json
Get-Content .\build\rmlui-native\guest\admission.json
```

Con un run CASM verificado del perfil `ring0-abi-probe-0.1`, por ejemplo
el conservado durante esta prueba:

```powershell
python .\tools\desktop\rmlui\native\qemu.py .\build\CASM\run-20261112-174958-944cb997
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-native
```

`qemu.py` prueba cuadro, teclado, raton, accion y cierre; tambien rechaza
un modulo W+X antes de copiar codigo de usuario. El run aprobado aparece
en su salida. `compare.py <run>` compara todos sus pixeles con el motor
HOST si ya se construyo la DLL. El visor comprueba la huella del modulo
contra la prueba aprobada antes de abrir la ventana. No instala en FAT32
fisico ni modifica entradas UEFI.

NMake solo ejecuta el build: los compiladores son clang/clang++, destino
`x86_64-unknown-none-elf`. No se enlaza MSVC, Windows SDK ni una biblioteca
Linux. `fetch.py` descarga archivos oficiales fijados por SHA256 y extrae
solo bajo `build/deps`. `fetch.py --check` comprueba ademas cada archivo
extraido contra el archivo fijado y las revisiones limpias de RmlUi/FreeType.
No instala nada globalmente. Los archivos se conservan para reproducir y
validar las fuentes; `build/` permanece fuera de Git.

Se usan declaraciones/tipos y rutinas de calculo de musl 1.2.5.
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
La misma copia de build limita los atlas a 256x256 frente a 1024x1024:
el temporal RGBA maximo pasa de 4 MiB a 256 KiB. No reduce resolucion de
glifos; puede aumentar el numero de paginas y limita el glifo maximo del
perfil. La escena verificada conserva sus 1,024,000 pixeles frente a HOST.

## Resultado medido

En el primer build de bibliotecas con Clang 23.1.2, antes del perfil
de atlas pequenos:

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

## Runtime y evidencia ejecutable

El inventario aislado de bibliotecas sigue mostrando servicios C;
`guest.py` los resuelve al enlazar el ejecutable. Su ELF final no tiene
simbolos pendientes. Los marcadores del enlazador tambien se resuelven.

`libc.py` compila 284 unidades de calculo de musl sin sus fuentes de
servicios del SO. Las rutinas UTF-8 usan copias intactas de sus funciones
y una copia de `internal.h` con MB_CUR_MAX=4, sin TLS/locales/pthreads.
`arena.c` proporciona 4 MiB con propiedad, alineacion y fusion de bloques;
`new.cpp` conecta toda la familia new/delete, incluida nothrow, al mismo
limite. OOM expone peticion, bytes vivos y pico, sin asignador alternativo.
`services.c` deniega disco y entorno, conserva errno y ofrece log serial.
El reloj admite inyeccion monotona; esta escena reducida lo deja en cero.

El arranque llama constructores C++. La seccion ejecutable especial de
libc++ queda en RX, no en los datos R. El build verifica secciones
ejecutables y proveedores matematicos: C++ debe usar libm SysV/SSE,
sin resolver por accidente sus funciones contra simbolos debiles del
runtime soft-float Rust. Ese error produjo triangulos deformados y queda
cubierto por una prueba. El marco C de dibujo solo pasa enteros/punteros,
sin valores float por la frontera entre ambos ABI.

La accion usa `action_vm.inc`, con su direccion de recurso reubicada en
una copia de build. Conserva validacion UJBC y region de 256 bytes.
El HOST compila el main.uj y lo incrusta; no hay Python en el invitado.

El perfil explicito `rmlui-native-v1` admite hasta 2 MiB de archivo,
tres regiones fijas RX/R/RW y sus limites originales de direcciones.
Los perfiles por defecto siguen limitados a 1 MiB. La operacion privada
9 presenta 1280x800 desde RW; no reinterpreta la operacion 6 de DOOM.
Se prueban puntero nulo/desalineado/fuera de rango, capacidad incorrecta,
op 6 denegada y modulo W+X rechazado antes de copiar codigo.

Medidas del ensayo: SBEF aproximadamente 1.77 MiB, framebuffer 4,096,000
bytes y pico de heap 3,028,176 bytes. El cargador privado usa paginas de
2 MiB y mapea 16 MiB de usuario, incluida la pila. El paquete CASM de
prueba ocupa unos 3,000 bytes: no es la prueba del objetivo nano-core
de 2 KiB ni la RAM total del sistema. La VM tiene 256 MiB configurados.

La comparacion completa con HOST tiene cero pixeles distintos. QEMU
verifica Enter, clic PS/2, accion nativa, cierre de recursos y rechazo
W+X. Los perfiles anteriores de sesion externa y DOOM conservan sus
bytes ensamblados frente a `2b3badd`.

Falta integrar este motor como superficie de DIRECTOR, los atajos
globales y la VM permanente; activar planificacion/animacion nativa y
recuperacion de errores/proceso; medir sesiones prolongadas y validar
el camino USB/METAL. Esta prueba de un cliente no acredita un planificador
general con preservacion de estado FPU entre tareas. No desplegarla
como reemplazo del escritorio fisico hasta completar esa integracion.

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
