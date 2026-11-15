# Acceso a archivos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Fija la frontera de acceso a imagenes y archivos sobre bloques.

Implementacion prevista: `userspace/services/files`; anillo 3, Rust. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Bloques, espacio de nombres y capacidad de directorio.
- Salida: Acceso limitado a datos o imagen de proceso.
- Aceptacion: Un servicio puede leer una imagen y rechaza una ruta fuera de su autoridad.
- Pendiente: Elegir que mecanismo queda en CASM y que politica va a Ring 3.
