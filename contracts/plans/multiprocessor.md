# Multiprocesador y perfil fisico

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Extiende el contexto por CPU y coordina acceso concurrente.

Implementacion prevista: `kernel/arch/x86_64/smp`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Base estable de una CPU, topologia y requisitos del equipo.
- Salida: CPU adicionales, sincronizacion y registro por CPU.
- Aceptacion: QEMU con varias CPU conserva estado y permisos antes de probar metal.
- Pendiente: Definir invariantes de sincronizacion y perfil de hardware.
