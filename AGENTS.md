# Trabajo en BMO-X2

- Trabajar en este arbol. No modificar BMO, Linux Reconstruido, SUPER GRAFO ni
  TALK-CPU-x86-64 como efecto secundario de una tarea de BMO-X2.
- Destino exclusivo x86-64. CASM para Ring 0; Rust para Ring 3.
- Carpetas nuevas en ingles. Tres ramas principales: `CASM/`, `kernel/` y
  `userspace/`; el codigo especifico de CPU vive en `kernel/arch/x86_64/`.
- La base del kernel se escribe desde cero en CASM. La inspiracion Linux es
  organizativa; heredar lecciones de BMO-X no significa copiar su kernel.
- Consultar SUPER GRAFO con `bmo-x2.ps1 -Accion resumen` y bajar al archivo
  necesario. La organizacion vive en `super-grafo/`, no en preferencias privadas.
  Las demas consultas se pasan con `-Accion consultar -Consulta <nombre>` y
  `-Argumentos <JSON>`; no hace falta abrir la interfaz para cada pregunta.
- Leer `docs/CASM-ROADMAP.md`, `CASM/STATUS-BMO-X2.md` y las notas del nodo antes
  de ampliar el compilador. No aplicar el parche 0.3 incompleto sin completar
  su verificador y sus pruebas como parte del mismo trabajo.
- Cada nodo declara responsabilidad, entradas, salidas, dependencias, estado y
  aceptacion en `super-grafo/nodes.json`. Mantenerlo al cambiar fronteras reales.
- No llamar terminado a lo heredado o disenado. Registrar HOST, QEMU o METAL
  con herramienta, fuente, build y limites de la evidencia.
- Los bytes CASM salen del emisor propio y pasan un verificador independiente.
  No debilitar una guarda para obtener una emision aceptada.
- Conservar el saludo de oro byte por byte al reorganizar metal64 0.2.
- Los numeros del ABI son contratos; RAM, CPU y aparatos se descubren o miden.
- Partir codigo por la pregunta que responde; no por numero arbitrario de lineas.
- Fuentes nuevas ASCII. Prosa del sistema en castellano sin acentos.
- Ejecutar comprobaciones pertinentes. Las pruebas Linux/QEMU no se sustituyen
  con simulaciones silenciosas de sus mecanismos en Windows.
- No desplegar a discos ni cambiar entradas de arranque para una comprobacion host.
