# Cargador SBEF

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Admite y mapea una imagen SBEF bajo el contrato del proceso.

## Contrato del nodo

- Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
- Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
- Aceptacion: El lector CASM y HOST coinciden en admision, mapa y rechazo. QEMU comprueba el prototipo externo x86-64 ABI 1 en CPL3 para sus layouts admitidos, permisos, copia, cero y rechazo W+X; la captura compara el plan HOST con PTE y marcos reales.
- Pendiente: La sonda LLVM solo reconoce layouts fijos RX, RX/R y RX/R/RW de una a tres regiones; ampliar el cargador CASM a una-ocho regiones, RVA, mapa dinamico, pila y rollback por proceso. La captura conectada aun requiere evidencia QEMU.
