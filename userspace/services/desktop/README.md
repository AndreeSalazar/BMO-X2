# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco y movimiento de ventanas.
- Aceptacion: QEMU verifica cuatro espacios, raton, foco y cuatro rechazos de permisos de pantalla y entrada.
- Pendiente: Leer SBEF desde disco, conectar el compositor completo y entregar entrada por eventos.
