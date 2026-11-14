# Escritorio y espacios de trabajo

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 3. Lenguaje previsto: Rust.

Compone superficies y gestiona ventanas y cuatro espacios inspirados en Ultra-LinuX.

## Contrato del nodo

- Entrada: Eventos de entrada, superficies de clientes y capacidad de pantalla.
- Salida: Cuadro en RAM, espacio activo, foco, movimiento de ventanas y peticion de cierre desde CABINA.
- Aceptacion: HOST exige presupuesto SBEF y puerta de sesion de hasta 2048 bytes. QEMU registra L1 por CPUID y verifica arranque FAT32, entrada, rechazo de permisos y reuso de cinco marcos.
- Pendiente: Entregar marcos al asignador, cargar un SBEF distinto, aislar procesos y conectar el compositor y el planificador.
