# Interrupciones de hardware

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Encamina IRQ con un contrato de entrada y reconocimiento separado de las excepciones.

Implementacion prevista: `kernel/arch/x86_64/interrupts`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: CPU preparada, tabla de vectores y controlador de interrupciones identificado.
- Salida: Evento acotado y retorno con el estado de CPU preservado.
- Aceptacion: Interrupcion de prueba y fuente muda en QEMU; no perder ni repetir reconocimientos.
- Pendiente: Controlador, vectores y politica de habilitacion antes de usar tiempo y dispositivos.
