# Faggin 64 bits

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Entrega contexto x86-64 a la misma entrada que utiliza UEFI.

Implementacion prevista: `kernel/boot/faggin/stage64`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Modo largo y mapa inicial de la ruta reset.
- Salida: Contexto, pila y recursos de arranque comprobables.
- Aceptacion: La entrada CASM observa modo largo y registra una excepcion controlada.
- Pendiente: Unir con la entrada despues de validar la IDT propia.
