# Excepciones x86-64

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Contiene fallos de CPU y preserva el estado necesario para explicar quien fallo y donde.

## Contrato del nodo

- Entrada: CPU preparada y marcos de excepcion definidos.
- Salida: Diagnostico, terminacion del proceso o parada controlada segun origen.
- Aceptacion: #UD/#PF de Ring 3 terminan ese proceso; el kernel conserva control y evidencia.
- Pendiente: La primera puerta #UD ya tiene evidencia. Faltan otros vectores, pilas de emergencia, diagnostico y contencion de Ring 3.
