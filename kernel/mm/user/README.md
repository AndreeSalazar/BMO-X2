# Memoria de usuario

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Valida rangos y copia datos entre anillos.

## Contrato del nodo

- Entrada: Espacio de usuario, direccion, longitud y permiso requerido.
- Salida: Copia acotada o error estable, con vida del rango controlada.
- Aceptacion: Un rango ajeno, desbordado o con pagina ausente se rechaza.
- Pendiente: Probar copia entre anillos y devolver paginas al asignador general.
