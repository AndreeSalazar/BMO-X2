# Buses, recursos y DMA

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 0. Lenguaje previsto: CASM.

Descubre xHCI y prueba transporte de comandos con reserva DMA y MMIO supervisora.

## Contrato del nodo

- Entrada: Inventario PCI, entrega UEFI, BAR, RTSOFF/DBOFF y diez paginas LoaderData.
- Salida: Respuesta No Op, descriptor de dispositivo y configuracion del primer USB2, parada y revocacion DMA en perfiles separados.
- Aceptacion: QEMU verifica transporte y enumeracion USB2 de alta/completa velocidad: lectura inicial de 8 B, Evaluate Context EP0, descriptores y parada. Sin dispositivos vence el plazo. Evidencia en evidence/enumeration-qemu.json.
- Pendiente: Metal confirma No Op y dos puertos; falta confirmar direccion y descriptores AMD. Pendientes configuracion de ambos HID, endpoints interrupt, hotplug asincrono e IOMMU.
