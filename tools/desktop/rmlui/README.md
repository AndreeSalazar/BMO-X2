# RmlUi + ULTRA-J: prueba HOST

Interfaz real RmlUi 6.3, FreeType y rasterizador Rust CPU de 1280x800.
El motor C++ recibe RML/RCSS, produce geometria y texto; el adaptador
dibuja dos fotogramas. Un click programado en el boton ejecuta `main.uj`
mediante el runtime HOST actual de ULTRA-J (Python, UJBC de 23 bytes).
La accion abre Window/Button, ejecuta dos metodos y cierra su region.
El resultado cambia el documento real y su imagen. No hay IPC.

## Reproducir en Windows / PowerShell 5.1

Desde la raiz de BMO-X2, con Python 3 + Pillow, Git, CMake, Rust, LLVM/clang-cl
y bibliotecas C++/Windows SDK de Visual Studio instalados:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\fetch.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\desktop\rmlui\build.ps1
python .\tools\desktop\rmlui\check.py
Start-Process .\build\rmlui-host\after.png
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
premultiplicada y recorte rectangular. Esta demostracion no valida
transformaciones, filtros, capas, imagenes externas, todas las reglas
RCSS ni rendimiento continuo. No es un navegador HTML/CSS completo.
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
freestanding. La vista HOST conserva exactamente los pixeles del primer
backend C++ del commit `6f61505` para los recursos fijados.

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
