# Cargador SBEF

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Admite y mapea una imagen SBEF bajo el contrato del proceso.

## Contrato del nodo

- Entrada: Bytes del ejecutable, limites, perfil SBEF y estado de CPU.
- Salida: Imagen mapeada con entrada y permisos comprobados o motivo de rechazo.
- Aceptacion: CASM y lector HOST coinciden en admision y rechazo. QEMU carga SBEF externo de una a ocho regiones a CPL3, comprueba permisos/BSS y recupera todas las paginas en salida o fallo.
- Pendiente: La sonda LLVM en kernel/loader/external_sbef.S solo cubre layouts fijos de una a tres regiones. Queda trasladar validacion a CASM e integrar mapa, pila, permisos y limpieza al ciclo de vida por proceso.
