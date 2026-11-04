# Interrupciones de hardware

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Encamina IRQ con un contrato de entrada y reconocimiento separado de las excepciones.

## Contrato del nodo

- Entrada: CPU preparada, tabla de vectores y controlador de interrupciones identificado.
- Salida: Evento acotado y retorno con el estado de CPU preservado.
- Aceptacion: Interrupcion de prueba y fuente muda en QEMU; no perder ni repetir reconocimientos.
- Pendiente: Controlador, vectores y politica de habilitacion antes de usar tiempo y dispositivos.
