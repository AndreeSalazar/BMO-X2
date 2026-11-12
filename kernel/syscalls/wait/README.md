# Puerta WAIT

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Duerme y despierta tareas por senal o vencimiento.

## Contrato del nodo

- Entrada: Objeto esperable, secuencia y plazo.
- Salida: Despertar, vencimiento o error con contexto preservado.
- Aceptacion: QEMU observa senal y plazo, sin espera activa ni perdida de un aviso concurrente.
- Pendiente: El numero ya responde -4 en QEMU. Probar bloqueo, senal y plazo con dos tareas.
