# Puerta CASM/Rust

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Recibe operaciones de Ring 3 y comprueba el contrato antes de tocar recursos.

## Contrato del nodo

- Entrada: ABI versionado, registros, capability y buffers declarados.
- Salida: Respuesta definida y retorno seguro a Ring 3.
- Aceptacion: Solicitud valida devuelve resultado; puntero/capacidad invalidos no comprometen al kernel.
- Pendiente: Convencion de llamada, entradas/salidas, estados y primera operacion observable.
