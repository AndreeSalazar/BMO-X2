# Planes de subsistemas

Estos documentos son contratos de diseno generados desde
`super-grafo/nodes.json`. Cada uno conserva su ID, responsabilidad,
entradas, salidas y prueba de aceptacion. La ruta de implementacion
prevista se muestra como una intencion, no como codigo disponible.

Los planes ya no crean carpetas vacias dentro del kernel. Cuando exista
una implementacion, su fuente y evidencia tendran un nodo y una ruta
reales bajo `kernel/` o `userspace/`, segun su privilegio.

Los planes de drivers de entrada, red y almacenamiento ahora declaran
destinos de Ring 3 bajo `userspace/drivers/`; el servicio de archivos
declara `userspace/services/files`. El nucleo conserva los mecanismos
de concesion y aislamiento. Es un cambio de reparto previsto; aun no
implementa esos servicios ni crea sus carpetas vacias.

La migracion esta registrada en
[plan-folders.json](../../super-grafo/migrations/plan-folders.json).
`tools/project.py generar` mantiene estos documentos sin recrear las
carpetas retiradas. `tools/workspace_audit.py` detecta archivos ausentes,
enlaces locales rotos, entradas Rust inexistentes, rutas de nodos
ausentes y residuos de las carpetas de plan retiradas.
