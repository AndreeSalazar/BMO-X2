# Entrada, pantalla y audio

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Ofrece recursos de entrada y salida a servicios autorizados.

Implementacion prevista: `userspace/drivers/input`; anillo 3, Rust. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Dispositivos descubiertos, buffers y eventos.
- Salida: Canales y ventanas de aparato acotados.
- Aceptacion: Pruebas de acceso, revocacion y fallo de servicio por dispositivo admitido.
- Pendiente: Metal confirma dos puertos conectados tras estabilizacion. Falta direccionar teclado y raton y activar ambos endpoints HID.
