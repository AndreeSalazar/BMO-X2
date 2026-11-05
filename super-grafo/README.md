# SUPER GRAFO es la mesa de BMO-X2

`genesis.json` guarda colores con motivo y posiciones del recorrido Genesis.
`tools/genesis_graph.py` los aplica preservando las demas posiciones. La
disposicion usa direccion Houdini; las cabeceras y conectores toman sus colores
de `tintes`, cuyo motivo aparece en el detalle. El color identifica una tarea,
no demuestra que su resultado este aprobado. Requiere SG actualizado.

`../BMO-X2.sg-workspace` establece esta raiz y el Taller CASM. Guardar el
espacio conserva la sesion local; guardar/reabrir no regenera este mapa ni
reacomoda sus nodos. El lanzador `-Accion abrir` abre ese archivo.

- `nodes.json`: catalogo versionado de responsabilidades y relaciones tipadas.
- `NOTAS.md`: descripcion por ruta; SUPER GRAFO la muestra en cada nodo.
- `orden.json`: posiciones y carpetas desplegadas en el formato real de SG.
- `MAPA.md` y `mapa.json`: fotografia generada por la consulta real `guardar`.
- `CATALOG.md`: ruta de trabajo CASM/kernel/Rust, generada desde `nodes.json`.

`bmo-x2.ps1 -Accion mapa` valida el catalogo, genera notas, pide a SG que
analice y guarde y aplica las posiciones explicitas de esta reconstruccion.
El generador no crea dependencias de codigo falsas ni modifica SUPER GRAFO.
La herramienta SUPER GRAFO se mejora en su propio proyecto por pedido del
propietario. `-Consulta casm` y el Taller leen ahora `CASM/catalog.json`:
jerarquia semantica del compilador, ademas de los nodos de archivos de este mapa.
La vista inicial deja las familias cerradas para leer sus nombres. Entrar en
CASM y despues en `src/` muestra los nodos de implementacion; el resto del
detalle conserva posiciones guardadas y se despliega cuando se necesita.

Las relaciones del plan se etiquetan `plan`; las de codigo, generacion y
verificacion describen la implementacion heredada. El analizador de SG muestra
sus propias dependencias reales. No se atribuye a su analisis lexico una
validacion semantica completa de Rust o de CASM.

Despues de «Save para SUPER GRAFO», usar `-Accion mapa` si se quiere recuperar
la distribucion inicial por etapas; el guardado normal prioriza crates Rust.
