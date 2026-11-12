# Dispositivos de red

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Expone colas y buffers de un dispositivo a un servicio autorizado.

## Contrato del nodo

- Entrada: Dispositivo, memoria asignada y permisos.
- Salida: Transporte acotado de tramas para Ring 3.
- Aceptacion: Prueba de envio, recepcion y aislamiento con dispositivo virtual.
- Pendiente: Elegir dispositivo y dejar protocolos en el servicio.
