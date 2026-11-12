# Diagnostico y recuperacion

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Registra fases, excepciones y causa de parada.

## Contrato del nodo

- Entrada: Fase de inicializacion o marco de excepcion.
- Salida: Registro acotado y decision de continuar, terminar proceso o parar.
- Aceptacion: QEMU identifica excepcion, origen y fase sin depender del escritorio.
- Pendiente: Emitir captura de excepcion y salida minima.
