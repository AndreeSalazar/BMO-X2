# Dispositivos de red

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Expone colas y buffers de un dispositivo a un servicio autorizado.

Implementacion prevista: `userspace/drivers/network`; anillo 3, Rust. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Dispositivo, memoria asignada y permisos.
- Salida: Transporte acotado de tramas para Ring 3.
- Aceptacion: Prueba de envio, recepcion y aislamiento con dispositivo virtual.
- Pendiente: Elegir dispositivo y dejar protocolos en el servicio.
