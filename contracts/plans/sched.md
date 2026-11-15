# Planificacion

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Gestiona ejecucion y espera con contexto y presupuesto definidos.

Implementacion prevista: `kernel/sched`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Tareas admitidas, memoria propia y fuente de tiempo.
- Salida: Cambio de contexto o espera con estado preservado.
- Aceptacion: Dos tareas no comparten contexto y una espera no gira en vacio; empezar por una CPU.
- Pendiente: Modelo de tarea, registros preservados y despertares; SMP queda para otra entrega.
