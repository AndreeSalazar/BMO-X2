# Limites del cargador SBEF

Ring 0 admite un ejecutable x86-64 con cabecera SBEF y un ABI conocido.
El cargador toma una vista inmutable durante la admision y la copia.
Valida el tamano, la cantidad de regiones, sus offsets, permisos y
entrada antes de comprometer mapeos. El plan de carga contiene solo
rangos y permisos. El gestor de memoria toma ese plan, reserva los
marcos, copia los bytes y publica la entrada en CPL3 al finalizar.

Si la operacion falla, la admision conserva el codigo de error y la
ubicacion del campo. El gestor revierte cualquier reserva parcial.
La revocacion trabaja sobre el espacio, las paginas y sus propietarios
una vez creada la imagen. El diario de fallos conserva datos de CPU
con tamano acotado. El supervisor puede convertirlos en un diagnostico
legible cuando exista una interfaz de consulta con capacidad.

ELF, PE, crates, simbolos, importaciones y dependencias se resuelven
en HOST o en herramientas de usuario. Los servicios de Ring 3 deciden
como interpretar sus propios formatos de datos. El cargador CASM de
SBEF externo sigue pendiente. El ensayo actual admite un SBEF embebido.

[Contrato binario](SBEF-HOST.md) | [Frontera de ejecucion](../docs/RING-BOUNDARY.md)
