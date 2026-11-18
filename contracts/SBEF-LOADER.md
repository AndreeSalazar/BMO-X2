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

El empaquetado en HOST normaliza la imagen y admite solo las regiones
que permite el perfil. Ring 0 vuelve a validar la estructura y aplica
los permisos al mapear. La admision no certifica la logica de las
instrucciones. El aislamiento, las capacidades y la recuperacion tras
fallos limitan lo que puede hacer el codigo una vez admitido.

HOST puede emitir una referencia de mapeo validada con
`python -B tools/sbef.py plan app.sbef`. El plan schema 1 detalla, por
region, el rango virtual alineado, paginas, tramo de archivo, BSS, cola
de pagina y total que debe quedar a cero, codigo de permisos y la
region/desplazamiento de entrada. La pila queda como asignacion separada
por proceso, sin fijar aun su tamano. Este resultado sirve para comparar
la futura admision CASM; no reserva memoria ni cuenta como carga en Ring 0.
El staging del escritorio conserva la salida como `desktop-load-plan.json`
y la incluye en `qemu-results.json` junto al presupuesto del caso.

`ZeroFillBytes` cubre desde el fin de los bytes del archivo hasta el fin
de las paginas mapeadas; incluye `BssBytes` y `PageTailBytes`. El mapa
describe permisos de usuario efectivos, no bits PTE ni marcos fisicos.

El ensayo externo en QEMU entrega el SBEF como modulo aparte. El
dispositivo loader de QEMU deposita longitud y bytes en 0x02000000
en una VM con 256 MiB. Un validador provisional x86-64 ensamblado
con LLVM comprueba ABI 1, codigo RX de hasta dos paginas, constantes
R/NX de una pagina y datos RW/NX de una pagina. El perfil conserva
las variantes con una o dos regiones. Valida toda la tabla antes
de copiar y deja a cero los bytes posteriores al contenido.
El verificador de captura de QEMU usa `load_plan` como referencia y
coteja la tabla completa de 512 PTE: marcos fisicos, permisos y flags
(ignorando solo A/D, que actualiza la CPU). Tambien compara todos los
bytes de paginas mapeadas con el archivo, BSS y cola a cero, verifica
la pila RW/NX y rechaza entradas PTE adicionales. El perfil de captura
acepta unicamente RX, RX/R o RX/R/RW en las direcciones y reservas
actuales. QEMU verifica las escrituras CPL3 en datos y BSS, y el rechazo
W+X en el offset 116 antes de copiar o activar CR3. Esta comprobacion
instrumenta la sonda LLVM; no sustituye el cargador CASM general.

El validador solo reconoce sus perfiles fijos de una a tres regiones;
no admite aun las direcciones RVA ni las cuatro o mas regiones que puede
emitir el nuevo perfil PE generico de HOST. Empaquetar un PE generico no
significa que QEMU o el kernel ya puedan ejecutarlo.

El perfil de escritorio lee `DESKTOP.SBF` desde FAT32 mediante UEFI y
entrega sus bytes a este validador. El escritorio ya se observo en
hardware. Quedan pendientes la integracion del cargador en CASM, los
mapeos generales y la asignacion y revocacion por proceso.

[Contrato binario](SBEF-HOST.md) | [Frontera de ejecucion](../docs/RING-BOUNDARY.md)
