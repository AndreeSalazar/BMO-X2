# Buses, recursos y DMA

> Generado desde super-grafo/nodes.json.

Estado: QEMU. Anillo: 0. Lenguaje previsto: CASM.

Descubre xHCI y prueba transporte de comandos con reserva DMA y MMIO supervisora.

## Contrato del nodo

- Entrada: Inventario PCI, entrega UEFI, BAR, RTSOFF/DBOFF y diez paginas LoaderData.
- Salida: Respuesta No Op comprobada, parada, Bus Master revocado y alias retirados.
- Aceptacion: QEMU verifica respuesta, reserva disjunta, parada y rechazo W+X. Evidencia en evidence/transport-qemu.json.
- Pendiente: Metal confirma No Op y dos puertos. QEMU verifica debounce adaptativo y limites; falta enumerar ambos HID, hotplug asincrono e IOMMU.
