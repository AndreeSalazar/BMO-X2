# Proceso y ciclo de vida

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: contrato. Lenguaje previsto: contrato.

Crea contexto de usuario, entra en Ring 3 y recoge recursos al terminar.

Implementacion prevista: `kernel/process`; anillo 0, CASM. Esta ruta no acredita codigo existente.

## Contrato del nodo

- Entrada: Espacio aislado, imagen de prueba y pila.
- Salida: Proceso con identidad y salida observable.
- Aceptacion: QEMU observa CPL3, retorno y fallo contenido, con recursos recuperados.
- Pendiente: Arrancar una imagen SBEF y reutilizar recursos en un segundo proceso.
