# SUPER GRAFO es la mesa de BMO-X2

- `nodes.json`: catalogo versionado de responsabilidades y relaciones tipadas.
- `NOTAS.md`: descripcion por ruta; SUPER GRAFO la muestra en cada nodo.
- `orden.json`: posiciones y carpetas desplegadas en el formato real de SG.
- `MAPA.md` y `mapa.json`: fotografia generada por la consulta real `guardar`.
- `CATALOG.md`: ruta de trabajo CASM/kernel/Rust, generada desde `nodes.json`.

`bmo-x2.ps1 -Accion mapa` valida el catalogo, genera notas, pide a SG que
analice y guarde y aplica las posiciones explicitas de esta reconstruccion.
El generador no crea dependencias de codigo falsas ni modifica SUPER GRAFO.
La vista inicial deja las familias cerradas para leer sus nombres. Entrar en
CASM y despues en `src/` muestra los nodos de implementacion; el resto del
detalle conserva posiciones guardadas y se despliega cuando se necesita.

Las relaciones del plan se etiquetan `plan`; las de codigo, generacion y
verificacion describen la implementacion heredada. El analizador de SG muestra
sus propias dependencias reales. No se atribuye a su analisis lexico una
validacion semantica completa de Rust o de CASM.

Despues de «Save para SUPER GRAFO», usar `-Accion mapa` si se quiere recuperar
la distribucion inicial por etapas; el guardado normal prioriza crates Rust.
