# ABI de aplicaciones

- `include/bmo_abi.h`: encabezado comun C/C++ de INVOKE y WAIT.
- `sysv/`: entrada ELF64, portal y vector HEX cotejado.
- `win64/`: entrada PE32+ freestanding y portal Rust para Microsoft x64.

El cargador inicia un SBEF con la pila alineada. Cada entrada establece
la convencion de llamada de su cliente. Ambos portales usan el mismo
[contrato de llamadas del kernel](../../../contracts/ABI.md).
