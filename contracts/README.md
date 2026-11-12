# Contratos: la frontera, antes del mecanismo

Estado: DISENO. Aun no hay ABI de BMO-X2 ejecutandose.

- **Destino:** x86-64; anchuras y modos de CPU explicitados por operacion.
- **HEX:** bytes exactos, fuente congelada, huellas, IR y verificador separado.
- **Imagen:** entrada, regiones, permisos, alineacion y trampas versionadas.
- **Puerta:** Rust Ring 3 pide operaciones mediante capacidades verificadas
  por CASM Ring 0; registros, numeros y errores todavia por definir y probar.
- **Memoria:** direccion virtual, fisica y direccion de un aparato no son
  intercambiables. Cesion, prestamo, devolucion y muerte tienen postcondiciones.
- **Evidencia:** HEREDADO, HOST, QEMU y METAL se registran por separado.

El ABI de dos puertas de BMO-X es referencia de aprendizaje. Su adopcion o
revision aqui exige una decision escrita; no copiar sus numeros sin contrato.

La [frontera BEF2 y ABI](ABI-BEF2.md) registra la referencia de BMO-X y las
pruebas de entrada y peticiones que debe superar BMO-X2.
