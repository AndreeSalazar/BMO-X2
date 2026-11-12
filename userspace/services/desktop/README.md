# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro presentado, espacio activo, foco y movimiento de ventanas.
- Aceptacion: Super con 1 a 4 cambia de espacio y conserva los clientes.
- Pendiente: Componer dos clientes en QEMU, presentar el cuadro y probar foco y movimiento.
