# Capas del escritorio

La carpeta de fuentes del servicio es `userspace/services/desktop/`.
El archivo `A:/BMO-X2/DESKTOP.SBF` es un ejecutable generado; no contiene
las carpetas de desarrollo. El lector UEFI actual espera esa ruta.

| Capa | Codigo actual | Responsabilidad |
|---|---|---|
| Pantalla y recursos | Capacidad de pantalla del ABI y adaptador `tools/desktop/session.rs` | Presentar en el framebuffer mediante las operaciones admitidas. |
| Composicion | `src/surface.rs` | Superficies, recorte y cuadro en RAM. |
| DIRECTOR | `src/lib.rs`, `src/keyboard.rs` | Ventanas, espacios, foco y atajos. |
| Vistas ULTRA-J | `../../../Ultra-J/ui/view.py` | Interpretar .ujh, comprobar geometria y generar listas UJVI. |
| Apariencia ULTRA-J | `../../../Ultra-J/ui/style.py` | Interpretar el perfil acotado .ujc, colores y propiedades soportadas. |
| Comportamiento | `../../../Ultra-J/compiler.py` y `runtime.py` | Construccion y ejecucion de los perfiles UJBC soportados. |

Las rutas de ULTRA-J parten de esta carpeta. El compilador visual vive
en HOST; las listas resultantes se presentan en Ring 3. La sonda actual
no integra todavia todo el compositor con el presentador ULTRA-J.

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
