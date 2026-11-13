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
como interpretar sus propios formatos de datos.

El ensayo externo en QEMU entrega el SBEF como modulo aparte. El
dispositivo loader de QEMU deposita longitud y bytes en 0x02000000
en una VM con 256 MiB. Un validador provisional x86-64 ensamblado
con LLVM comprueba ABI 1, una region RX de hasta dos paginas y una
region opcional de solo lectura y no ejecutable de una pagina.
Valida ambas regiones y la entrada antes de copiar. QEMU coteja
los bytes y los permisos de las paginas y verifica el rechazo W+X
de la segunda region antes de copiar codigo o activar CR3.

Quedan pendientes el transporte desde un archivo leido por BMO-X2,
la integracion en CASM, las regiones de datos RW con BSS y la asignacion y
revocacion por proceso. Este ensayo usa un cliente y dos permisos fijos.

[Contrato binario](SBEF-HOST.md) | [Frontera de ejecucion](../docs/RING-BOUNDARY.md)
