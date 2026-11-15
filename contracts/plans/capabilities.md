# Capacidades

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Concede autoridad explicita y comprueba propietario, derechos y vigencia.

Implementacion prevista: `kernel/capabilities`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Peticion admitida y recursos con propietario.
- Salida: Handle concedido, operacion comprobada o motivo de rechazo.
- Aceptacion: Handle inventado, revocado o de otro proceso falla por su motivo; la autoridad no se hereda implicitamente.
- Pendiente: Layout del handle, tabla, generacion, transferencia y revocacion.
