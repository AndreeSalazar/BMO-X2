# Comunicacion entre procesos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Transporta mensajes y prestamos con autoridad y limites comprobados.

Implementacion prevista: `kernel/ipc`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Procesos aislados, capacidades y buffers declarados.
- Salida: Mensaje recibido o error de permisos, medida o vida util.
- Aceptacion: Rechaza destino ajeno, rango invalido y prestamo vencido sin filtrar memoria.
- Pendiente: Primer canal y sus postcondiciones de cierre/muerte antes de servicios mayores.
