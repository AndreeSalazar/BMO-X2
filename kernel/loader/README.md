# Cargador SBEF

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Admite y mapea una imagen SBEF bajo el contrato del proceso.

## Contrato del nodo

- Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
- Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
- Aceptacion: El lector HOST y el prototipo x86-64 ensamblado con LLVM comprueban admision, mapa y rechazo en perfiles fijos. QEMU verifica en CPL3 PTE/marcos/permisos reales, bytes inmutables, rechazo W+X y la region RW mutable; evidencia run-desktop-media-32f9f2682ded.
- Pendiente: La sonda LLVM solo reconoce layouts fijos RX, RX/R y RX/R/RW de una a tres regiones; ampliar el cargador CASM a una-ocho regiones, RVA, mapa dinamico, pila y rollback por proceso. La evidencia es QEMU y excluye comparar bytes RW tras ejecutar; falta validar el cargador CASM general.
