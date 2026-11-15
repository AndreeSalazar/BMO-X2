# Faggin 32 bits

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Prepara segmentos, pila y paginacion inicial para modo largo.

Implementacion prevista: `kernel/boot/faggin/stage32`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Entrega protegida de 32 bits y memoria reservada.
- Salida: Tablas y salto al segmento de codigo de 64 bits.
- Aceptacion: QEMU verifica registros de control y rangos de las reservas.
- Pendiente: Emitir la transicion de 32 a 64 bits con vector independiente.
