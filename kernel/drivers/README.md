# Frontera de dispositivos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Aisla mecanismos de dispositivos del resto del kernel y explicita acceso a puertos/MMIO/DMA.

## Contrato del nodo

- Entrada: Hardware identificado, regiones concedidas e interrupciones comprobadas.
- Salida: Operaciones acotadas con estado, tiempo limite y motivo de fallo.
- Aceptacion: Aparato ausente o mudo no bloquea el kernel; permisos y DMA se prueban por separado.
- Pendiente: Empezar con un dispositivo simple exigido por el arranque; no trasladar la investigacion GPU a esta base.
