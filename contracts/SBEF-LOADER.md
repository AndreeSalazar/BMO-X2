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
(ignorando solo A/D, que actualiza la CPU). Compara bytes exactos y
relleno a cero en las regiones inmutables RX y R. Verifica la traduccion,
marco y permisos de RW, pero no compara su contenido despues de ejecutar:
el cliente ya pudo cambiar datos inicializados y BSS. Comprueba la pila
RW/NX y rechaza entradas PTE adicionales. El perfil de captura acepta
unicamente RX, RX/R o RX/R/RW en las direcciones y reservas actuales.

En el perfil ULTRA-J, la sonda coteja tambien el bloque de solo lectura
que contiene la longitud de `ACTION.UJB` y sus bytes exactos. El ensayo
`run-desktop-media-c5cf4aae8961` verifico una pagina RX y la ausencia de
la antigua entrada de pila en la ranura de la segunda pagina RX.

El run `run-desktop-media-32f9f2682ded` ejecuto en QEMU el SBEF Hoja de
10 174 bytes desde FAT32 y aprobo el caso normal y el rechazo de W+X
(offset 116). El cotejo cubrio cuatro paginas SBEF, 10 042 bytes de
archivo inmutable, 2 246 bytes de relleno inmutable a cero y la PTE de la
pagina RW; el contenido de esa unica pagina mutable se excluyo de la
comparacion posterior a la ejecucion. La VM uso 1024 MiB. Es evidencia
de la sonda y este perfil, no de arranque fisico ni del cargador CASM
general.

El [validador estructural CASM Native](../kernel/loader/sbef_validate.casm)
lee una longitud medida y una copia acotada de la cabecera y la tabla de
regiones. Comprueba el perfil SBEF predeterminado, con hasta ocho regiones,
y devuelve un identificador de rechazo y su offset. El entorno que lo
integre debe conservar inmutables la tabla y el contenido hasta terminar
la copia. El validador inspecciona la declaracion de ISA. El chequeo
efectivo de CPU y la asignacion corresponden al cargador.

El banco `tools/boot/casm_sbef_qemu.py` compila la fuente con CASM Native
dentro de un invitado Linux, verifica el ELF con el auditor independiente
y compara los recibos con HOST. El ejecutable del banco usa un adaptador
de entrada y salida Linux. La fuente del validador mantiene esa E/S fuera
de la rutina. [Evidencia diferencial](../Reports/casm-sbef-validation-qemu.json).

Con `--freestanding`, la primera VM compila y el HOST audita y convierte
el ELF. Una segunda VM llama al modulo con codigo RX y datos RW/NX. La
entrada [CASM freestanding](../kernel/loader/sbef_validate_entry.casm)
recibe los bytes de la envoltura en 296 celdas `u64` desde `0x10000018`.
El llamador valida la marca inicial en `0x10000958` y escribe alli la
cantidad real de celdas antes de cada llamada. El stub Native fija el
retorno en RAX segun SysV y usa la pila del llamador. El banco reserva
8 454 144 bytes virtuales de datos y mide una pagina residente con Linux
al completar los 29 casos.
[Evidencia freestanding](../Reports/casm-sbef-freestanding-qemu.json).

La sonda `tools/boot/sbef_ring0_qemu.py` llama a ese mismo modulo
auditado despues de ExitBootServices. El perfil QEMU usa dos paginas de
codigo RX, una pagina de datos RW/NX y una pila de 1 MiB con guarda. El
modulo solo puede acceder a la primera pagina de su ventana de datos en
este perfil. Se verifican los 29 recibos y cuatro trampas (`#UD`, pagina
de guarda, escritura sobre RX y ejecucion en NX). Al finalizar restaura el
mapa y comprueba el borrado de las 267 paginas reservadas. El ensayo usa
vectores preparados por HOST.
[Evidencia post-EBS](../Reports/casm-sbef-ring0-qemu.json).

En el perfil `--external` de la misma sonda, UEFI lee un SBEF externo
desde FAT32. Ring 0 le da al validador CASM una copia de la cabecera y
la tabla, comprueba ABI 1 y el perfil ISA efectivo y rechaza antes de
publicar si excede 64 paginas de regiones. La copia usa un alias supervisor
RW/NX que se retira antes de entrar a CPL3. Se comprueban ocho regiones,
una de dos paginas, copias a ambos lados del limite de pagina, BSS y pila.
El fallo de escritura en R/NX y la salida por la puerta de prueba ejecutan
la misma rutina de restauracion y borrado, incluida la reserva FAT32.
Esta ruta usa una sesion aislada por arranque de QEMU y una puerta de prueba
para cerrar. El cliente ya usa SYSCALL para INVOKE y WAIT por el ABI 1
candidato. Un retorno con pila invalida usa la misma limpieza. WAIT
duerme hasta el plazo del PIT y reconoce una secuencia ya publicada.
El ensayo `--peer` prueba el despertar por senal con dos contextos que
comparten codigo RX y tienen pilas y CR3 propios. Queda pendiente la
admision independiente del segundo SBEF y la integracion con el gestor
de procesos.
[Evidencia de carga y salida](../Reports/casm-sbef-external-ring3-qemu.json).

En pruebas separadas, la sonda externa LLVM cierra y vuelve a abrir el
escritorio en los mismos cinco marcos y verifica su borrado en cada salida.
La sonda ABI embebida recupera dos marcos tras un fallo de usuario y los
reutiliza con un segundo cliente. El cargador general tiene pendiente
reunir ambas rutas de recuperacion bajo un mismo contrato de proceso.

La sonda CASM post-EBS admite en QEMU el SBEF v2 de cuatro regiones que
HOST emite desde un PE MSVC con `DIR64`. El temporizador observa el
contador modificado en CPL3. El caso de control conserva la direccion
anterior y causa un fallo de lectura. La sonda LLVM de escritorio sigue
limitada a sus perfiles fijos de una a tres regiones.
[Evidencia de reubicacion](../Reports/host-msvc-rebase-qemu.json).

El perfil `--msvc-dll` hace que el mismo cargador de prueba mapee seis
regiones de un EXE y una DLL, mas la pila. El cliente llama dos veces a
la exportacion resuelta por HOST y comprueba el estado del modulo. El
control cambia su region RW a R y provoca un fallo de usuario. La salida
y el fallo restauran la puerta y el mapa y borran la reserva completa.
[Evidencia de la DLL](../Reports/host-msvc-dll-qemu.json).

La sonda `--msvc-tls` mantiene un solo mapa de proceso y arranca dos
hilos secuenciales con pilas distintas. Cambia la base GS antes de la
entrada de cada hilo y la restaura al final. HOST prepara la plantilla
de la prueba y dos regiones TLS. QEMU verifica que la segunda conserva
sus valores iniciales despues de la escritura del primer hilo y que el
control compartido sale con error. Queda pendiente el TLS del gestor de
hilos. [Evidencia de TLS](../Reports/host-msvc-tls-qemu.json).

El perfil de escritorio lee `DESKTOP.SBF` desde FAT32 mediante UEFI y
entrega sus bytes a este validador. El escritorio ya se observo en
hardware. Quedan pendientes la integracion del cargador en CASM, los
mapeos generales y la asignacion y revocacion por proceso.

[Contrato binario](SBEF-HOST.md) | [Frontera de ejecucion](../docs/RING-BOUNDARY.md)
