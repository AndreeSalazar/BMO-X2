# Buses, recursos y DMA

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 0. Lenguaje previsto: CASM.

Descubre xHCI y prueba transporte de comandos con reserva DMA y MMIO supervisora.

## Contrato del nodo

- Entrada: Inventario PCI, entrega UEFI, BAR, RTSOFF/DBOFF y diez paginas LoaderData.
- Salida: Respuesta No Op, descriptor de dispositivo y configuracion del primer USB2, parada y revocacion DMA en perfiles separados.
- Aceptacion: QEMU verifica transporte, seleccion de puertos y rechazos. METAL: foto del 16-11 confirma descriptores en AMD puerto 2, CC 01, CS 64 B y MPS 8; Reports/metal-ep0-20261116.json.
- Pendiente: Pendientes configuracion de interfaces HID, endpoints interrupt, informes de ambos dispositivos, hotplug asincrono e IOMMU.
