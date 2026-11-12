# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco y movimiento de ventanas.
- Aceptacion: QEMU verifica una sesion CPL3 con cuatro espacios, teclado PS/2 y restauracion del foco.
- Pendiente: Arrancar el SBEF externo y conectar el compositor completo, entrada por eventos y telemetria de Ring 0.
