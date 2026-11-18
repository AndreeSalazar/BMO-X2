# SBEF (Super BEF)

Estado de BMO-X2: prototipo HOST de empaquetado y lectura. SBEF es la
evolucion propia de BEF2 de BMO-X.
BEF2 aporta el modelo de regiones con permisos fijos, un indice de anexos
y una puerta de admision acotada. Su cabecera y su ABI se documentan en la
[referencia del padre](ABI-BEF2.md).

TALK-CPU aporta el puente y los contratos de entrega de la CPU. ULTRA
LinuX aporta el metodo para comparar toolchains y verificar artefactos.
SUPER GRAFO conserva los nodos de cada entrega y el mapa de la emision
CASM. [Registro de transferencia](../heritage/TRANSFER.md).

## Fronteras

| Frontera | Que recibe | Que entrega |
|---|---|---|
| Arranque Ring 0 | Cuerpo x86-64 emitido por CASM y verificado | El puente entrega modo largo y el contexto de arranque. El paquete de entrada actual usa FAGRAW64 y debe medir menos de 512 bytes. |
| Carga de Ring 3 | Ejecutable x86-64 empaquetado en SBEF | El cargador comprueba el encabezado y prepara la entrada, la pila y las paginas del proceso. |
| Peticiones Ring 3 a Ring 0 | Registros y argumentos del ABI | `INVOKE` opera sobre una capacidad y `WAIT` espera un evento con plazo. |

CASM emite `.hex` para las instrucciones y los datos propios del kernel.
El verificador independiente reconstruye los bytes y los vincula con
la fuente, la IR y los offsets. En ejecucion, el cargador escrito en CASM
lee el SBEF como bytes binarios. GCC, Clang, Rust y otros toolchains pueden
producir programas si el enlazador y el empaquetador entregan el SBEF
acordado y el runtime usa el ABI de BMO-X2.

El compilador corre durante el build. Por ejemplo, el emisor COBOL
x86-64 de BMO-X puede ser un productor de codigo para el futuro
empaquetador SBEF. El cargador de Ring 0 admite la imagen, configura
paginas y pila, y entrega el punto de entrada a la CPU en CPL3.
Las bibliotecas y el runtime de COBOL se enlazan para ese ABI. La
prueba de compatibilidad exige un programa real y sus dependencias.

El [perfil x86-64 del HOST](SBEF-HOST.md) implementa el puente de build
ELF64 estatico -> SBEF. El [ABI 1](ABI.md) y la admision CASM ya se
ejercitan en QEMU con un SBEF embebido de una region. El cargador de
imagenes externas y el bloqueo de WAIT siguen pendientes.

La direccion futura de productores y destinos se especifica en
[IR BMO](IR-BMO.md). La IR es entrada del HOST; Ring 0 recibe el paquete
nativo de su propia ISA y ABI.

[Responsabilidades del cargador y del gestor de memoria](SBEF-LOADER.md).

## Encabezado y perfil ISA

- La cabecera es little-endian de 32 bytes. SBEF v1 heredado requiere cero
  en flags/reservado y significa `x86-64-v1`; SBEF v2 conserva los mismos
  offsets y almacena el ID ISA en el u32 del offset 24. Los IDs 1-4 significan
  `x86-64-v1` a `x86-64-v4`; el u32 del offset 28 sigue reservado y debe ser
  cero. La arquitectura de maquina sigue siendo ELF 62, exclusivamente x86-64.
- ABI, version de contenedor y perfil ISA son campos distintos. Un ID ISA
  desconocido se rechaza antes de mapear.
- Regiones de codigo RX, constantes R+NX, datos RW+NX y memoria a cero
  RW+NX. Los permisos se derivan de la clase de region. La entrada debe
  caer dentro del codigo ejecutable. Separar las regiones a nivel de pagina.
- La declaracion ISA identifica el nivel minimo requerido; no demuestra por
  desensamblado que todos los opcodes del productor respeten ese nivel. El
  HOST registra opciones y fixtures del productor. El contrato exige que Ring 0
  compruebe CPUID, CR4 y XCR0 antes de ejecutar; los niveles v1-v4 siguen la
  jerarquia del
  [x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI/blob/master/x86-64-ABI/low-level-sys-info.tex).
- Extensiones de fabricante y requisitos no representados por los cuatro
  niveles se rechazan o quedan fuera del perfil; no se infieren del nombre
  x86-64.
- La direccion futura del HOST puede compartir adaptadores y una IR BMO
  validada, pero cada ISA necesitara su propio backend, ABI y contrato de
  paquete. Esta version de SBEF mantiene arquitectura 62 y no admite POWER.
  La IR no equivale a traducir automaticamente un ELF/PE x86-64 ya enlazado;
  el cambio de ISA requiere fuente/IR compatible o un traductor binario aparte.
- La primera imagen de prueba sera estatica y minima. Las relocaciones,
  los anexos y las dependencias que se admitan se deciden segun el primer
  programa real que los necesite.

El lector debe responder ante cualquier secuencia de bytes con una
admision valida o un rechazo acotado. La primera clase admitida sera el
ejecutable SBEF x86-64. Un archivo de otro formato sigue siendo un archivo
de datos para las herramientas de Ring 3. Si SBEF incorpora recursos
opacos, la validacion del contenedor comprueba su tamano y su ubicacion.
El consumidor del recurso interpreta su contenido.

El cargador valida el archivo y su presupuesto antes de mapear. Debe
comprobar que el encabezado y la tabla caben, que los calculos de rangos
no desbordan, que las regiones no se solapan y que la imagen pide una
CPU y un ABI admitidos. Las decisiones de confianza y de capacidades
pertenecen a una politica separada de la forma del archivo. Los bytes
usados al mapear deben corresponder a la imagen validada.

## Orden de trabajo y congelacion

1. Ampliar CASM para un contexto de entrada, una pila propia y una
   excepcion controlada. Cada operacion requiere IR, vector manual,
   verificacion, casos de rechazo y evidencia QEMU. SUPER GRAFO enlaza
   la fuente con los bytes y el resultado observado.
2. Preparar memoria y permisos para un proceso aislado. Probar que
   el proceso entra en Ring 3 y que su fallo deja operativo al kernel.
3. Producir un SBEF minimo con un empaquetador HOST y comprobarlo con
   un lector independiente. Probar en QEMU que CASM coincide con el
   lector al admitir y rechazar imagenes. Medir el camino desde la
   entrega del puente hasta la primera instruccion de Ring 3.
4. Probar `INVOKE` con una operacion observable y `WAIT` con una senal y
   un vencimiento. Verificar capacidades, limites de argumentos,
   registros, retorno al usuario y aislamiento ante fallos.
5. Ejecutar la misma peticion desde C con GCC y Clang y luego desde
   Rust, C++ y un programa COBOL minimo del padre. Comparar resultados
   y permisos en el mismo kernel.

Congelar el encabezado y el ABI al cerrar esas pruebas. Publicar los
offsets, permisos, registros, numeros de las dos puertas, codigos de
estado y reglas de compatibilidad. Conservar un vector binario de oro
y mutaciones de version, truncado, desborde, solape y permisos. Conservar
tambien casos de capacidad invalida, buffer fuera de rango y plazo
vencido. Un cambio incompatible requiere una version nueva.
