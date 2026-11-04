# Contrato HEX preciso

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Define el significado de HEX preciso: bytes exactos y evidencia de su correspondencia.

## Contrato del nodo

- Entrada: Fuente congelada, perfil, IR, bytes y origen de herramientas.
- Salida: Contrato fuente -> IR -> HEX -> bytes, con entrada, regiones, medidas y huellas.
- Aceptacion: Roundtrip HEX/bytes exacto y rechazo de IR, opcode, desplazamiento o dato alterado.
- Pendiente: Extender el contrato actual a trampas y relocaciones del kernel; HEX no acredita por si solo ejecucion.
