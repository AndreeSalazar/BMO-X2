# RmlUi + ULTRA-J: prueba HOST

Interfaz real RmlUi 6.3, FreeType y rasterizador CPU de 1280x800.
El motor C++ recibe RML/RCSS, produce geometria y texto; el adaptador
dibuja dos fotogramas. Un click programado en el boton ejecuta `main.uj`
mediante el runtime HOST actual de ULTRA-J (Python, UJBC de 23 bytes).
La accion abre Window/Button, ejecuta dos metodos y cierra su region.
El resultado cambia el documento real y su imagen. No hay IPC.

## Reproducir en Windows / PowerShell 5.1

Desde la raiz de BMO-X2, con Python 3 + Pillow, Git, CMake, LLVM/clang-cl
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
- `preview.cpp`: motor, dibujo CPU y callback de evento.
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
Antes de emitir SBEF faltan: inventario de simbolos/runtime C++ y FreeType,
asignador acotado, servicios de archivo/tiempo, puente Rust con propietarios
de memoria explicitos, entrada DIRECTOR, presentacion de framebuffer y
pruebas de aislamiento. El presupuesto actual del escritorio no alcanza
por el mero hecho de cambiar de encabezado. Mantenerlo como puerta de
aceptacion; no debilitar guardas. Ring 0 no incorpora RmlUi ni FreeType.
No se modifica el volumen A: ni las entradas UEFI para esta prueba.

## Licencias

RmlUi: MIT. Fuentes LatoLatin: licencias incluidas en el paquete.
FreeType: elegida FreeType License, copiada junto con su aviso.
This software is based in part on the work of the FreeType Team.
Los textos completos se copian desde las revisiones fijadas.

Referencia: [integracion oficial RmlUi](https://mikke89.github.io/RmlUiDoc/pages/cpp_manual/integrating.html).
