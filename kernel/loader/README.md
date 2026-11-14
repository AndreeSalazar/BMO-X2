# Cargador SBEF

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Admite y mapea una imagen SBEF bajo el contrato del proceso.

## Contrato del nodo

- Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
- Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
- Aceptacion: El lector independiente y CASM coinciden en el vector de oro y rechazos, con QEMU en Ring 3.
- Pendiente: La sonda LLVM en kernel/loader/external_sbef.S lee el SBEF entregado desde FAT32. Queda trasladar el cargador a CASM y asignar marcos y capacidades por proceso.
