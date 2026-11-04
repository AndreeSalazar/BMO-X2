# Servicios Rust

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 3. Lenguaje previsto: Rust.

Aloja servicios con autoridad concedida y politica fuera del kernel.

## Contrato del nodo

- Entrada: Runtime Rust y capacidades de sus recursos.
- Salida: Operaciones de servicio con errores y limites definidos.
- Aceptacion: La caida o revocacion de un servicio no concede acceso a recursos ajenos.
- Pendiente: Primer servicio de diagnostico; entrada, disco y escritorio llegan por separado.
