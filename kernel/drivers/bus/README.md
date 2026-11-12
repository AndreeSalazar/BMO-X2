# Buses, recursos y DMA

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Descubre recursos de dispositivos y delimita su acceso y DMA.

## Contrato del nodo

- Entrada: Perfil de plataforma y recursos descubiertos.
- Salida: Recursos con propietario y transferencia controlada.
- Aceptacion: Un dispositivo de prueba queda limitado a sus recursos y ventanas DMA.
- Pendiente: Elegir primer dispositivo y politica segun hardware medido.
