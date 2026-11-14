# Entrada, pantalla y audio

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Ofrece recursos de entrada y salida a servicios autorizados.

## Contrato del nodo

- Entrada: Dispositivos descubiertos, buffers y eventos.
- Salida: Canales y ventanas de aparato acotados.
- Aceptacion: Pruebas de acceso, revocacion y fallo de servicio por dispositivo admitido.
- Pendiente: QEMU abre CABINA por USB con xHCI activo. WAIT detecta el evento al despertar del PIT y Rust recibe cuatro informes. Faltan reciclado de colas, raton y controladores fisicos.
