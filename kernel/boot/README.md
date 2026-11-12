# Arranque del kernel

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Recibe una maquina y una imagen bajo un contrato de entrega verificable.

## Contrato del nodo

- Entrada: Modo largo y CPL0 entregados por el puente UEFI, con un paquete de entrada CASM verificado.
- Salida: Primera entrada propia bajo 512 bytes, seguida por inicializacion y diagnostico del kernel.
- Aceptacion: Paquete menor de 512 bytes con cabecera incluida. QEMU confirma llegada y efecto en Ring 0.
- Pendiente: Genesis y la parada propia tienen evidencia QEMU. Sigue el contexto propio y una excepcion controlada.
