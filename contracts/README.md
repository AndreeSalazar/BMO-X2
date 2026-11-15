# Contratos: la frontera, antes del mecanismo

Estado mixto: ABI y SBEF tienen perfiles ejecutados en QEMU; los planes
de subsistemas y la gestion general de procesos siguen incompletos.

- **Destino:** x86-64; anchuras y modos de CPU explicitados por operacion.
- **HEX:** bytes exactos, fuente congelada, huellas, IR y verificador separado.
- **Imagen:** entrada, regiones, permisos, alineacion y trampas versionadas.
- **Puerta:** Rust Ring 3 pide operaciones mediante capacidades verificadas
  por Ring 0; [ABI.md](ABI.md) registra los numeros, registros y limites actuales.
- **Memoria:** direccion virtual, fisica y direccion de un aparato no son
  intercambiables. Cesion, prestamo, devolucion y muerte tienen postcondiciones.
- **Evidencia:** HEREDADO, HOST, QEMU y METAL se registran por separado.

El ABI de dos puertas de BMO-X es referencia de aprendizaje. Su adopcion o
revision aqui exige una decision escrita; no copiar sus numeros sin contrato.

[SBEF](SBEF.md) registra el diseno del encabezado propio y los criterios
para congelarlo junto con el ABI. [BEF2 y ABI de BMO-X](ABI-BEF2.md)
conserva la referencia del padre.

El [backlog de implementacion](../docs/RING0-PLAN.md) conserva el trabajo
pendiente. Los documentos duplicados por subsistema fueron eliminados.

[ULTRA-J 0.1](../Ultra-J/FORMAT.md) define bytecode, tema binario y recuperacion de
objetos por regiones en la primera sonda HOST.
