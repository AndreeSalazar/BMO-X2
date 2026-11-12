# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: HOST. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco y movimiento de ventanas.
- Aceptacion: HOST verifica cuatro espacios, foco, movimiento y pixels compuestos.
- Pendiente: Arrancar el SBEF externo, presentar el cuadro y recibir la capacidad de entrada.
