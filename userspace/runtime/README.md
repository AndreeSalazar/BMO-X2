# Runtime minimo Rust

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 3. Lenguaje previsto: Rust.

Permite ejecutar un programa Rust aislado usando el ABI concedido por CASM.

## Contrato del nodo

- Entrada: Imagen admitida, pila, datos y ABI BMO-X2.
- Salida: Entrada de usuario, llamadas y finalizacion/panico controlados.
- Aceptacion: Programa no_std entra en Ring 3, recibe respuesta del kernel y falla de forma contenida.
- Pendiente: Target, entrada, enlace, wrappers del ABI y manejo de panico; aun no hay crate.
