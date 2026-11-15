# Diagnostico y recuperacion

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Registra fases, excepciones y causa de parada.

Implementacion prevista: `kernel/diagnostics`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Fase de inicializacion o marco de excepcion.
- Salida: Registro acotado y decision de continuar, terminar proceso o parar.
- Aceptacion: QEMU identifica excepcion, origen y fase sin depender del escritorio.
- Pendiente: Emitir captura de excepcion y salida minima.
