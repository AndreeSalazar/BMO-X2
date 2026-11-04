# Planificacion

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Gestiona ejecucion y espera con contexto y presupuesto definidos.

## Contrato del nodo

- Entrada: Tareas admitidas, memoria propia y fuente de tiempo.
- Salida: Cambio de contexto o espera con estado preservado.
- Aceptacion: Dos tareas no comparten contexto y una espera no gira en vacio; empezar por una CPU.
- Pendiente: Modelo de tarea, registros preservados y despertares; SMP queda para otra entrega.
