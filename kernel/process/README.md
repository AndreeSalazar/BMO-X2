# Proceso y ciclo de vida

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 0. Lenguaje previsto: CASM.

Crea contexto de usuario, entra en Ring 3 y recoge recursos al terminar.

## Contrato del nodo

- Entrada: Espacio aislado, imagen de prueba y pila.
- Salida: Proceso con identidad y salida observable.
- Aceptacion: QEMU observa CPL3, retorno y fallo contenido, con recursos recuperados.
- Pendiente: Demostrar primero una imagen fija de prueba.
