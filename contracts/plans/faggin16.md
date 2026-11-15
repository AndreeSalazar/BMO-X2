# Faggin 16 bits

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Prepara el primer salto desde reset en la ruta propia.

Implementacion prevista: `kernel/boot/faggin/stage16`; anillo contrato, CASM arranque. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Estado de reset, ROM y espacio de pila temporal.
- Salida: A20, GDT y entrada protegida de 32 bits.
- Aceptacion: QEMU registra el cambio de modo y el destino del salto.
- Pendiente: Definir el formato y la emision CASM de la etapa de 16 bits.
