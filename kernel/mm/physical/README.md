# Memoria fisica

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Distingue memoria util, reservada y marcos asignados.

## Contrato del nodo

- Entrada: Mapa de arranque con limites verificados.
- Salida: Asignacion y devolucion de marcos con propietario.
- Aceptacion: No asigna una reserva, detecta doble devolucion y recupera marcos al salir.
- Pendiente: Definir unidad, limites y primera prueba de asignacion.
