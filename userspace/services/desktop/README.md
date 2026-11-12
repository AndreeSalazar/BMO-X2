# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco y movimiento de ventanas.
- Aceptacion: HOST verifica atajos y foco. QEMU verifica 4096 pixeles de dos superficies compuestas en CPL3.
- Pendiente: Arrancar el SBEF externo y conectar presentacion continua, teclado y telemetria de Ring 0.
