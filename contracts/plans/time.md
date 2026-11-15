# Reloj y plazos

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Ofrece tiempo monotono y plazos medibles antes de introducir planificacion.

Implementacion prevista: `kernel/time`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Fuente de tiempo descubierta y mecanismo de interrupcion comprobado.
- Salida: Lecturas y vencimientos con unidad y origen declarados.
- Aceptacion: Plazo vence y tiempo no retrocede; frecuencia observada y coste de lectura registrados.
- Pendiente: Elegir fuente y calibracion sin suponer frecuencias del Ryzen.
