# Puerta INVOKE

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Despacha operaciones mediante capacidades del proceso activo.

Implementacion prevista: `kernel/syscalls/invoke`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Registros del ABI, handle, operacion y argumentos.
- Salida: Estado y valor o rechazo acotado.
- Aceptacion: Operaciones autorizadas y denegadas dan el resultado esperado sin afectar otro proceso.
- Pendiente: Generalizar capacidades por proceso y probar una operacion con buffer.
