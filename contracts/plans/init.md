# Inicializacion del kernel

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Ordena fases y precondiciones del kernel sin esconder los fallos de un subsistema.

Implementacion prevista: `kernel/init`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Contexto boot y resultados de CPU, excepciones y memoria.
- Salida: Estado de fase listo o fallo con nombre y motivo.
- Aceptacion: Una fase invalida impide ejecutar las siguientes; diagnostico identificable en QEMU.
- Pendiente: Primera secuencia de inicializacion escrita en CASM despues de fijar el perfil de kernel.
