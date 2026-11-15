# Bloques y almacenamiento

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Entrega bloques mediante un dispositivo acotado.

Implementacion prevista: `userspace/drivers/storage`; anillo 3, Rust. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Dispositivo de bloques, rangos y capacidad.
- Salida: Lecturas y errores de dispositivo reproducibles.
- Aceptacion: Lectura valida y fuera de rango en un disco virtual con imagen de prueba.
- Pendiente: Separar los bloques del sistema de archivos.
