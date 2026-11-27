# Capas del escritorio

El candidato nuevo une la politica DIRECTOR de Rust con RmlUi nativo
y una lectura UEFI real del SBEF desde FAT32. Sus archivos de prueba
viven en A:/BMO-X2/DESKTOP/; el arranque anterior permanece separado.
Ver [arranque nativo y estado del metal](../../../docs/NATIVE-DESKTOP-BOOT.md).
La politica usa un marcador de superficie inmutable, sin alias al
framebuffer mutable del motor; el presentador sigue siendo RmlUi/Rust.

La carpeta de fuentes del servicio es `userspace/services/desktop/`.
El archivo `A:/BMO-X2/DESKTOP.SBF` es un ejecutable generado; no contiene
las carpetas de desarrollo. El lector UEFI actual espera esa ruta.

| Capa | Codigo actual | Responsabilidad |
|---|---|---|
| Pantalla y recursos | Capacidad de pantalla del ABI y adaptador `tools/desktop/session.rs` | Presentar en el framebuffer mediante las operaciones admitidas. |
| Composicion | `src/surface.rs` | Superficies, recorte y cuadro en RAM. |
| Bienvenida Ring 3 | `src/welcome.rs`, perfil `-Welcome` de `tools/build-desktop.ps1` | Entrada visual breve tras la admision y pruebas de permisos, antes del escritorio. |
| DIRECTOR | `src/lib.rs`, `src/keyboard.rs` | Ventanas, espacios, foco y atajos. |
| Vistas ULTRA-J | `../../../Ultra-J/ui/view.py` | Interpretar .ujh, comprobar geometria y generar listas UJVI. |
| Apariencia ULTRA-J | `../../../Ultra-J/ui/style.py` | Interpretar el perfil acotado .ujc, colores y propiedades soportadas. |
| Comportamiento | `../../../Ultra-J/compiler.py` y `runtime.py` | Construccion y ejecucion de los perfiles UJBC soportados. |

Las rutas de ULTRA-J parten de esta carpeta. El compilador visual vive
en HOST; las listas resultantes se presentan en Ring 3. La sonda actual
no integra todavia todo el compositor con el presentador ULTRA-J.

## VERRANO y la GPU

[VERRANO](../graphics/verrano/lib.rs) aloja el verificador de lotes
de Ring 3 inspirado en `DrawBackend` de BMO-X. Una
aplicacion puede entregar un cuadro ya dibujado o enviar un lote de
dibujo. DIRECTOR decide que superficie recibe foco y ocupa la pantalla.
El backend grafico procesa el lote y la salida de pantalla presenta el
resultado. Los controladores de cada fabricante viven con el dispositivo.

HOST valida, reduce y vuelve a validar el subconjunto SPIR-V del
triangulo antes de entregarlo a Vulkan en el banco Windows. Admite las
etapas de vertice y fragmento del perfil acotado. El controlador del
dispositivo genera el codigo de maquina de los shaders.
[Registro SPIR-V de Khronos](https://registry.khronos.org/SPIR-V/).

El verificador Rust recibe el titular autenticado y la tabla de
buffers del servicio. Comprueba cada rango y el presupuesto de
vertices antes de entregar el lote completo. Las pruebas HOST usan un
backend de prueba. Queda conectar el verificador a la tabla real del
servicio y a un backend nativo, incluida la recuperacion del dispositivo.
[Prueba del triangulo y comparacion CPU/GPU](../../../Reports/verrano-triangle-host.json).

### BSF estatico y cuadros dinamicos

El banco `run.ps1 -Textured` usa el lector y escritor `BSF1` del
BMO-X original. `-BmoRoot` indica ese arbol. Por defecto usa el
directorio hermano `BMO`. El adaptador conserva los dos shaders SPIR-V
validados, comprueba los hashes del contenedor y coteja los archivos
recuperados con la salida de HOST. El perfil fija un sampler 2D en
set 0, binding 0. La tabla de interfaces de BSF1 describe buffers.
El contrato de textura se comprueba en el SPIR-V y en el perfil Vulkan.

Vulkan crea la tuberia una vez y carga dos texturas de 2 por 2 en
memoria local del dispositivo en un envio inicial. El comando de cada
cuadro se arma con el angulo y un descriptor ya preparado. La RTX
muestrea la textura y dibuja. La CPU lee el cuadro en este banco para
comprobar el resultado despues. El BSF probado lleva SPIR-V portable.
El controlador Vulkan genera el codigo de la GPU al crear la tuberia.
[Evidencia del BSF y las texturas](../../../Reports/verrano-texture-bsf-host.json).

La [sonda Ring 3 de VERRANO](../../../Reports/verrano-resident-qemu.json)
usa un backend por software para el mismo contrato de seleccion.
Un lote presenta ranura y generacion. VERRANO resuelve la textura
solo si pertenece al cliente y el backend ya confirmo su residencia.
La tabla de recursos pertenece al servicio. El backend asincrono
debera conservar cada recurso hasta que el dispositivo termine.

En QEMU, el mismo lote selecciona dos recursos de color distintos.
Antes de presentar, la sonda exige el rechazo de una generacion
caducada, una textura ajena, una textura sin residencia y una ranura
fuera de la tabla. La captura del framebuffer comprueba 4096
pixeles. Quedan pendientes el lector BSF en el proceso de usuario,
la tabla de recursos del controlador y la presentacion RTX nativa.

```powershell
.\tools\build-desktop.ps1 -VerranoProbe -AbiRun $abiRun
```

La estructura .ujh, la apariencia .ujc y el comportamiento .uj son
entradas diferentes. Cambiar el tema no debe introducir politica de
ventanas en el parser de estilos ni logica CSS dentro de Ring 0.

El perfil .ujc actual admite posiciones y dimensiones en px, fondo,
color, radio, escala de fuente y alineacion limitada. No implementa
CSS completo, cascada general, flexbox ni grid. Para reutilizar un motor
existente hay que adaptar layout, texto/fuentes, dibujo, asignaciones,
eventos y dependencias al entorno Ring 3 admitido.

LLVM puede construir un backend nativo adaptado como ELF64 para HOST;
HOST admite el perfil y genera SBEF. ELF64 describe codigo y datos: no
interpreta hojas de estilo. MSVC no es requisito para esa ruta. Las
hojas .ujc actuales son datos del compilador visual Python y no requieren
ningun compilador C++ para procesarse.

Referencias: [CSS y sus modulos](https://www.w3.org/TR/css/),
[generacion de codigo y objetos LLVM](https://llvm.org/docs/CodeGenerator.html).

La separacion de `Ultra-J/ui/` conserva el formato UJVI y su resultado
byte por byte. `Ultra-J/view.py` mantiene la CLI y las importaciones que
usan package.py y los scripts de construccion. No cambia los archivos
del volumen de arranque ni la distribucion del escritorio instalado.

## Origen del experimento HOST y candidato nativo

`tools/desktop/rmlui/` prueba RML/RCSS con RmlUi + FreeType y un
rasterizador CPU nativo en Windows HOST. Sus recursos viven en
`Ultra-J/examples/rmlui-desktop/`; la accion usa el runtime HOST actual.
El dibujo comun vive en `src/rmlui.rs`, seguro y no_std. El adaptador
HOST C++ lo llama mediante `raster.h`/`raster.rs`, prestando buffers por
llamada. El mismo codigo paso una sonda SBEF en CPL3 con pixeles identicos
a HOST. La variante nativa posterior ya tiene runtime acotado, acciones
UJBC nativas y politica DIRECTOR. No sustituye el escritorio antiguo ni
acredita USB fisico: la migracion completa de aplicaciones sigue pendiente.
Ver el README del adaptador y su evidencia reproducible.

El adaptador C++ de sesion `tools/desktop/rmlui/engine.cpp` recibe una
tabla de recursos en memoria, reloj monotono y destino de dibujo
prestado; enlaza la geometria con el dibujador Rust. Su objeto se
audita sin llamadas directas Kernel32. El runtime enlazado sigue siendo
Windows, no un motor SBEF ya admitido. La prueba `live.py` verifica
entrada por opacidad, animacion de ancho/color, movimiento reducido,
puntero y callback ULTRA-J HOST, mas cierre y rechazos. El siguiente
plazo de RmlUi se expone al cliente para integrarlo luego con WAIT.

El dibujador acepta Alpha8 para atlas blancos premultiplicados, con
RGBA para datos de color. Conserva los pixeles y reduce el payload del
ejemplo un 75%; el camino Alpha8 tambien paso QEMU en CPL3. La sesion
HOST ofrece `frame_if_due` para no limpiar ni rasterizar un destino
preservado cuando no hay cambios ni plazos vencidos. Entrada, animacion
o un destino perdido fuerzan trabajo. Esta politica de reposo aun no
forma parte del escritorio instalado ni de la sonda QEMU del motor completo.

## Gato Ring 0, bienvenida Ring 3, escritorio

El gato CASM permanece intacto. La prueba compara sus dos cuadros de
entrada y luego confirma que la bienvenida Rust llama WAIT desde CPL3.
El gato acredita ese hito del arranque, no el funcionamiento de todos
los dispositivos. La admision SBEF y las comprobaciones de permisos
preceden a la bienvenida; no hay pantallas que simulen pruebas de hardware.

La bienvenida dibuja la marca BMO X2 y tres segmentos. Dura como maximo
54 ticks del PIT del perfil normal (aproximadamente 540 ms a 100 Hz),
con hasta ocho respuestas de protocolo por fase. No gira esperando al
reloj: usa WAIT. ACK y RESEND PS/2 no cuentan como teclas. La primera
entrada real omite la animacion y se entrega al decodificador normal,
incluidos prefijos y bytes de raton. QEMU comprueba F2: abre CABINA al
entrar y demuestra que la tecla no se perdio. Esto no prueba entrada
USB en AMD. Se dibujan solo los segmentos nuevos entre fases.

Este perfil es optativo y usa el lanzador ULTRA-J actual; no incluye
RmlUi completo ni modifica el escritorio instalado en FAT32. La opcion
`-Welcome` exige `-UltraJ` para conservar los presupuestos actuales.
La medida QEMU conserva 16 KiB de regiones de usuario y agrega 783 bytes
al archivo SBEF del perfil base (10,408 frente a 9,625 bytes). La pila,
framebuffer y estructuras supervisoras no estan incluidos en esas regiones.
La futura presentacion RmlUi puede sustituir esta apariencia en Ring 3
sin cambiar el gato ni introducir logica visual en Ring 0.

Desde la raiz, PowerShell 5.1 (usar el Python que tenga instalado):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build-desktop.ps1 `
    -Session -External -Sheet -UltraJ -Welcome `
    -AbiRun build/CASM/run-20261112-174958-944cb997
python .\tools\boot\doom_qemu.py build/CASM/run-20261112-174958-944cb997 `
    build/desktop/desktop-welcome.sbef `
    --intro build/CASM/run-20261112-045636-c461240e `
    --session-gate build/desktop/session-gate.bin `
    --external-loader build/desktop/external-sbef.bin --desktop-welcome
```

El segundo comando imprime un run aprobado. Para verlo en ventana:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Run <ruta-del-run>
```

El informe del run conserva tres casos: transicion completa, rechazo
W+X y salto con F2. La prueba de bienvenida no certifica la VM ULTRA-J,
DOOM ni las funciones del escritorio que ya tienen sus propias pruebas.
