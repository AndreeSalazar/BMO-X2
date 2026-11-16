# RmlUi + ULTRA-J: prueba HOST

Interfaz real RmlUi 6.3, FreeType y rasterizador Rust CPU de 1280x800.
El adaptador C++ `engine.cpp` recibe recursos en memoria, tiempo y
eventos mediante `engine.h`. No incluye APIs Windows, reloj de pared,
escritura de imagenes ni acceso a disco. Su objeto se audita por separado.
El runtime C++ y las bibliotecas enlazadas todavia dependen de Windows.

`live.py` demuestra una sesion real con entrada por opacidad de 200 ms,
animacion RCSS de 400 ms, transiciones de color, puntero y accion
ULTRA-J HOST (Python/UJBC).
El boton abre Window/Button, ejecuta dos metodos y cierra su region.
La entrada anterior `preview.cpp` se conserva como prueba de dos cuadros.
Ambas entradas comparten el dibujador y un propietario exclusivo de
las interfaces globales de RmlUi. No hay IPC.

## Reproducir en Windows / PowerShell 5.1

Desde la raiz de BMO-X2, con Python 3 + Pillow, Git, CMake, Rust, LLVM/clang-cl
y bibliotecas C++/Windows SDK de Visual Studio instalados:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\fetch.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\build.ps1
python .\tools\desktop\rmlui\check.py
python .\tools\desktop\rmlui\live.py
python .\tools\desktop\rmlui\audit.py
Start-Process .\build\rmlui-live\animation.gif
```

`fetch.ps1` descarga solo versiones fijadas en `dependencies.lock.json`.
`build.ps1` verifica revision y arbol limpio. Compila con Clang C++17,
FreeType estatico y RmlUi estatico dentro de una DLL HOST. No instala
paquetes globales. El cache y los builds viven bajo `build/`, ignorado
por Git; no se incluyen copias de motores ni binarios en las fuentes.

## Fronteras y paquete

- `Ultra-J/examples/rmlui-desktop/main.rml`: estructura visual.
- `style.rcss`: apariencia; RCSS es el dialecto de RmlUi, no todo CSS web.
- `main.uj`: accion independiente de apariencia.
- `preview.cpp`: motor C++, recursos y callback de evento.
- `engine.cpp` / `engine.h`: sesion C++ con ABI C, reloj inyectado y eventos.
- `memory_files.h`: lectura exclusivamente de recursos declarados, con cursores acotados.
- `renderer.h`: geometria/recursos compartidos y presentacion por el dibujador Rust.
- `owner.h`: propietario unico del estado global RmlUi, en el hilo de interfaz.
- `live.py`: entrega de recursos desde HOST, prueba de sesion y animacion real.
- `raster.h` / `raster.rs`: puente C sin retener punteros; buffers prestados por llamada.
- `userspace/services/desktop/src/rmlui.rs`: dibujo Rust no_std, seguro, sin heap ni SO.
- `preview.py`: compila UJBC, empaqueta recursos/licencias y mide el proceso.
- `check.py`: rechazo de accion, entrada ausente y reinicializacion exitosa.

HOST produce `build/rmlui-host/package/manifest.json` con hashes y tamanos
de DLL, fuentes, documentos, accion y licencias. `before.png`, `after.png`
y `results.json` quedan al lado del paquete. No se abre una ventana
interactiva: se renderiza y se prueba un click programado.
La DLL aun depende del runtime de Windows; Python/Pillow tampoco se
incluyen. El manifiesto declara `sbef:false` y `ring3_ready:false`.
Empaquetar no traduce servicios de Windows a BMO-X2 automaticamente.

El backend admite triangulos, texturas generadas para fuentes, mezcla
premultiplicada y recorte rectangular. Transformaciones, filtros,
capas/mascaras y shaders que requieran un backend avanzado se reportan
como fuera del perfil y la sesion se bloquea hasta cerrar. No se
valida todo RCSS ni rendimiento continuo. No es un navegador HTML/CSS completo.
Los enlaces de navegacion laterales representan el diseno, sin acciones.

## Medidas y siguiente frontera

`results.json` separa bytes de paquete, framebuffer (4,096,000 bytes),
geometria/texturas del adaptador y memoria del proceso Python+nativo.
Los tiempos incluyen escribir BMP; no son latencia de entrada ni FPS.
Contadores del adaptador en cero al cerrar no prueban ausencia de todas
las fugas del proceso. La evidencia conservada registra una ejecucion,
no un presupuesto garantizado para QEMU o METAL.

Rust puede dirigir el escritorio usando un puente C estrecho al motor
C++. LLVM/Clang compila ese motor; no sustituye su runtime ni su ABI.
`audit.py` inventaria las importaciones reales de la DLL y el rechazo
HOST, sin borrar dependencias ni declarar admitido un binario incompatible.
Faltan asignador acotado, biblioteca C++/FreeType freestanding, servicios
de archivo/tiempo, puente de eventos Rust con propietarios de memoria
explicitos, entrada DIRECTOR y pruebas de aislamiento. El presupuesto actual no alcanza
por el mero hecho de cambiar de encabezado. Mantenerlo como puerta de
aceptacion; no debilitar guardas. Ring 0 no incorpora RmlUi ni FreeType.
No se modifica el volumen A: ni las entradas UEFI para esta prueba.

## Primera pieza comprobada en Ring 3

El dibujador comun admite triangulos, UV, texturas RGBA premultiplicadas
y recorte. El mismo archivo Rust se compila en la DLL HOST y en un SBEF
freestanding. En la migracion `c4bb4f1`, la vista HOST con los recursos
de entonces conservo exactamente los pixeles del backend C++ inicial
`6f61505`. El ejemplo actual agrega animaciones; esas imagenes registran
la migracion, sin congelar el tema.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\guest.ps1 `
    -AbiRun build/CASM/run-20261112-174958-944cb997
python .\tools\desktop\rmlui\audit.py
```

La sonda QEMU presenta una superficie de prueba de 16x16 ampliada, desde
CPL3 mediante la capacidad de pantalla existente. Compara todos sus
pixeles con HOST (degradado, arista compartida, recorte y textura) y
verifica rechazo W+X. El bucle final `pause` solo mantiene la sonda
observable hasta que el capturador termina QEMU; no es el lazo del escritorio.

Resultado medido: SBEF 7,085 bytes, regiones RX/R 12,288 bytes mapeados,
mas 4,096 bytes de pila de usuario reservada por el fixture. No contiene
RML, fuentes ni el motor C++ completo. El target freestanding usa las
rutinas de coma flotante de compiler_builtins, sin introducir SSE ni
requisitos nuevos de contexto SIMD. ELF sin simbolos sin resolver.
No representa RAM total del sistema; excluye las estructuras supervisoras,
framebuffer y coste de QEMU. Evidencia: `Ultra-J/evidence/rmlui-ring3.json`.

### Para convertirlo en el escritorio permanente

1. Compilar RmlUi/FreeType y su runtime contra servicios propios; la DLL
   Windows inventariada sigue rechazada. No mapear sus importaciones a ciegas.
2. Definir un perfil de carga medido para el motor; el actual tiene
   limites por region de 8 KiB RX, 4 KiB R y 4 KiB RW. No basta con
   elevar el limite global de HOST ni renombrar la DLL.
3. Conectar entrada DIRECTOR y acciones ULTRA-J nativas al arbol vivo;
   conservar foco, Super+Q, espacios y cierre de recursos. El callback
   Python actual es exclusivamente HOST.
4. Presentar superficies con invalidacion, limitar memoria/texturas y
   usar INVOKE/WAIT en la sesion real; probar cierre, fallos y entrada.
5. Solo entonces seleccionar el perfil como escritorio de arranque y
   validar en METAL. La prueba actual no reemplaza DESKTOP.SBF instalado.

## Licencias

RmlUi: MIT. Fuentes LatoLatin: licencias incluidas en el paquete.
FreeType: elegida FreeType License, copiada junto con su aviso.
This software is based in part on the work of the FreeType Team.
Los textos completos se copian desde las revisiones fijadas.

Referencia: [integracion oficial RmlUi](https://mikke89.github.io/RmlUiDoc/pages/cpp_manual/integrating.html).

## Sesion C++ alimentada por HOST: bmo-ui-memory-v1

Es un contrato experimental de aplicacion, separado del ABI del kernel.
`bmo_ui_open` recibe una tabla de recursos y un callback sin excepciones.
Nombres y bytes permanecen validos e inmutables hasta `bmo_ui_close`.
El cliente mantiene los buffers: no hay transferencia implicita de propiedad.
No se admiten rutas absolutas, directorios ni `..`. Limites: ocho recursos,
dos MiB cada uno, ocho MiB totales y 32 cursores abiertos. Se rechazan
recursos ausentes y advertencias/errores de analisis RCSS; no se llama
al sistema de archivos del anfitrion desde este adaptador.

`bmo_ui_frame(ns, pixels, count)` recibe tiempo monotono y un buffer
exclusivo XRGB de 1280x800. Solo toma prestado el destino durante esa
llamada. No crea un segundo framebuffer nativo ni retiene su puntero.
Se rechazan retrocesos de reloj y dimensiones incorrectas antes de escribir.
El dibujador limita geometria y texturas a 16 MiB cada una; esto no es
un limite global del heap de RmlUi/FreeType/STL, que sigue pendiente.

`bmo_ui_input` entrega puntero o Enter al contexto RmlUi. El click
del boton invoca ULTRA-J una vez y actualiza las clases visuales.
DIRECTOR seguira siendo propietario de atajos globales y foco.
El callback no puede cerrar ni reentrar destructivamente en el motor.
`bmo_ui_close` comprueba que RmlUi libero geometria, texturas y cursores.
No se acepta una segunda sesion ni se permite a la entrada antigua
sustituir las interfaces mientras esta sesion vive. API de un solo hilo.

`bmo_ui_motion(0)` activa movimiento reducido; la vista queda estable
sin ejecutar la animacion de entrada. `bmo_ui_next_delay_ms` expone el
siguiente plazo pedido por RmlUi; `UINT32_MAX` indica que no solicita
actualizaciones. El futuro lazo Ring 3 debe combinarlo con entrada y
su presupuesto de cuadros mediante WAIT; el adaptador no llama a Ring 0.
Debe respetar el limite de duracion del WAIT existente; `UINT32_MAX`
es una senal del motor, no una duracion que se pase directamente al ABI.

Estados: 0 correcto, 1 ciclo de vida/reentrada, 2 argumento, 3 recursos,
4 motor/perfil visual, 5 retroceso del reloj. Un fallo de render invalida
ese cuadro (el cliente no debe presentarlo) y obliga a cerrar antes de
continuar. Los punteros del ABI C son de un llamador confiable y deben
referir buffers validos, alineados y con la longitud declarada.

`live.py` compara anchos interpolados y pixeles de la transicion de color,
prueba movimiento reducido, rechazo de recursos/RCSS/transformaciones/
filtros, accion rechazada, reentrada, cierre y reinicializacion. Genera
`build/rmlui-live/animation.gif` con fotogramas reales del motor y su
informe. El GIF repite la demostracion; la animacion del motor termina.
Esta es evidencia HOST. La logica ULTRA-J sigue en el runtime Python
actual; la DLL aun se rechaza para SBEF y no se instala en FAT32.
