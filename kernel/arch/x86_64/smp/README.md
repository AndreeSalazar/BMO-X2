# Multiprocesador y perfil fisico

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Extiende el contexto por CPU y coordina acceso concurrente.

## Contrato del nodo

- Entrada: Base estable de una CPU, topologia y requisitos del equipo.
- Salida: CPU adicionales, sincronizacion y registro por CPU.
- Aceptacion: QEMU con varias CPU conserva estado y permisos antes de probar metal.
- Pendiente: Definir invariantes de sincronizacion y perfil de hardware.
