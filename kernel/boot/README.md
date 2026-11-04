# Arranque del kernel

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Recibe una maquina y una imagen bajo un contrato de entrega verificable.

## Contrato del nodo

- Entrada: Estado x86-64, memoria y framebuffer entregados por una cadena de arranque especificada.
- Salida: Entrada del kernel CASM, diagnostico y estado de fallo controlado.
- Aceptacion: QEMU muestra entrada real y rechaza contexto/imagen incompatibles; se conserva recuperacion.
- Pendiente: Elegir la cadena de carga y contexto; entry.casm es solo una sonda compilada y verificada en host.
