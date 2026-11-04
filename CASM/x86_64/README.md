# CASM para el metal privilegiado

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: host. Lenguaje previsto: CASM especificacion.

Define la ampliacion del lenguaje que permite expresar el kernel sin perder control de bytes y efectos.

## Contrato del nodo

- Entrada: Programas minimos de CPU, memoria y excepciones que exige BMO-X2.
- Salida: Semantica, IR, emision propia y verificacion de operaciones privilegiadas.
- Aceptacion: Cada operacion tiene codificacion independiente, efecto autorizado y prueba QEMU positiva/negativa.
- Pendiente: MMIO/volatile, CR/MSR, puertos, atomicos, descriptores, entradas de excepcion y cambios de anillo.
