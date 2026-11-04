# Comunicacion entre procesos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Transporta mensajes y prestamos con autoridad y limites comprobados.

## Contrato del nodo

- Entrada: Procesos aislados, capacidades y buffers declarados.
- Salida: Mensaje recibido o error de permisos, medida o vida util.
- Aceptacion: Rechaza destino ajeno, rango invalido y prestamo vencido sin filtrar memoria.
- Pendiente: Primer canal y sus postcondiciones de cierre/muerte antes de servicios mayores.
