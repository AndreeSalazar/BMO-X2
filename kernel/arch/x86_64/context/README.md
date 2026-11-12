# Estado de CPU y cambio de contexto

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Prepara descriptores, TSS y estado de CPU que debe preservarse.

## Contrato del nodo

- Entrada: Capacidades de CPU, pila y contrato de contexto.
- Salida: Marcos separados y estado preservado por tarea.
- Aceptacion: QEMU comprueba pilas, registros y estado de CPU al cambiar de tarea.
- Pendiente: Definir marcos y probar primero una CPU.
