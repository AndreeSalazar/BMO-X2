# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco y movimiento de ventanas.
- Aceptacion: QEMU verifica cuatro espacios, teclado y raton PS/2, foco por clic y escala 2x en 1280x800.
- Pendiente: Cargar SBEF externo, conectar el compositor, repintar solo el area del cursor y entregar entrada por eventos.
