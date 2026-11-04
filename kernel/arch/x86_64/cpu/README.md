# CPU x86-64

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Descubre capacidades CPU y prepara descriptores y estado privilegiado con limites explicitos.

## Contrato del nodo

- Entrada: Contrato de arranque y operaciones privilegiadas CASM.
- Salida: Estado CPU apto para excepciones y aislamiento de Ring 3.
- Aceptacion: CPUID y limites observados en QEMU; no se confunde el perfil del Ryzen con todo x86-64.
- Pendiente: GDT/TSS, modos, registros de control y requisitos minimos del perfil inicial.
