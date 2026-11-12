# Contexto de entrega

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Valida el contexto recibido y fija la pila inicial propia.

## Contrato del nodo

- Entrada: Modo largo, CPL0 y contexto del puente.
- Salida: Contexto comprobado y pila acotada.
- Aceptacion: QEMU acredita pila propia y rechazo de un contexto invalido.
- Pendiente: Versionar campos y emitir la primera validacion en CASM.
