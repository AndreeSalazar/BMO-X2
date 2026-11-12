# Faggin 64 bits

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Entrega contexto x86-64 a la misma entrada que utiliza UEFI.

## Contrato del nodo

- Entrada: Modo largo y mapa inicial de la ruta reset.
- Salida: Contexto, pila y recursos de arranque comprobables.
- Aceptacion: La entrada CASM observa modo largo y registra una excepcion controlada.
- Pendiente: Unir con la entrada despues de validar la IDT propia.
