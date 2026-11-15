# Estado de CPU y cambio de contexto

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Prepara descriptores, TSS y estado de CPU que debe preservarse.

Implementacion prevista: `kernel/arch/x86_64/context`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Capacidades de CPU, pila y contrato de contexto.
- Salida: Marcos separados y estado preservado por tarea.
- Aceptacion: QEMU comprueba pilas, registros y estado de CPU al cambiar de tarea.
- Pendiente: Definir marcos y probar primero una CPU.
