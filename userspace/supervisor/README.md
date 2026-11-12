# Supervisor Rust de Ring 3

> Generado desde super-grafo/nodes.json.

Estado: DISENO. Anillo: 3. Lenguaje previsto: Rust.

Ordena, configura y recupera servicios desde CPL3.

## Contrato del nodo

- Entrada: Proceso Rust admitido, runtime y capacidades concedidas.
- Salida: Servicios iniciados, vigilados y recuperados con autoridad acotada.
- Aceptacion: Reinicia un servicio caido sin elevar privilegio ni heredar autoridad implicita.
- Pendiente: Implementar despues de arrancar SBEF y verificar INVOKE y WAIT.
