# Entrada, pantalla y audio

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Ofrece recursos de entrada y salida a servicios autorizados.

## Contrato del nodo

- Entrada: Dispositivos descubiertos, buffers y eventos.
- Salida: Canales y ventanas de aparato acotados.
- Aceptacion: Pruebas de acceso, revocacion y fallo de servicio por dispositivo admitido.
- Pendiente: El escritorio muestra el estado xHCI tras UEFI. QEMU verifica teclado y raton USB en sondas separadas. Faltan uso simultaneo, reconexion y validacion fisica.
