# Espacios y permisos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Establece espacios virtuales separados y permisos por pagina.

## Contrato del nodo

- Entrada: Marcos fisicos, rangos y permiso solicitado.
- Salida: Paginas de kernel y usuario con proteccion de escritura y ejecucion.
- Aceptacion: QEMU impide escritura de codigo y ejecucion de datos.
- Pendiente: Probar fallos de permisos desde CPL3 y separar codigo RX de datos RW y NX.
