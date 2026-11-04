# Memoria y aislamiento

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Asigna paginas y separa memoria del kernel, procesos y aparatos.

## Contrato del nodo

- Entrada: Mapa de memoria, capacidades CPU e intervalos reservados.
- Salida: Paginas con propietario, tablas, permisos y devolucion definidos.
- Aceptacion: Ring 3 no escribe kernel ni ejecuta datos NX; rangos invalidos y desbordes se rechazan.
- Pendiente: Asignador, paginacion, TLB, vida de prestamos y pruebas de muerte del proceso.
