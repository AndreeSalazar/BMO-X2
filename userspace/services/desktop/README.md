# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 3. Lenguaje previsto: Rust.

Gestiona ventanas y cuatro espacios con atajos inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, clientes y capacidades de pantalla.
- Salida: Espacio activo, foco y movimiento de ventanas.
- Aceptacion: Super con 1 a 4 cambia de espacio y conserva los clientes.
- Pendiente: Ejecutar dos clientes en Ring 3 y probar foco y movimiento.
