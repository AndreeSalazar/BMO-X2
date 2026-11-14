# Entrada, pantalla y audio

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Ofrece recursos de entrada y salida a servicios autorizados.

## Contrato del nodo

- Entrada: Dispositivos descubiertos, buffers y eventos.
- Salida: Canales y ventanas de aparato acotados.
- Aceptacion: Pruebas de acceso, revocacion y fallo de servicio por dispositivo admitido.
- Pendiente: QEMU verifica 260 informes de teclado y, en otra sonda, movimiento y foco con raton USB. Faltan uso simultaneo, reconexion y validacion en controladores fisicos.
