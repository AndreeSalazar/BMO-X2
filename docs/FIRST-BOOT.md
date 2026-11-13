# Primer hito: una entrada propia y un fallo explicado

## Primera prueba en hardware

El primer objetivo fisico es llegar a una parada controlada en Ring 0 desde
el firmware UEFI x86-64 y poder explicar en que fase quedo el equipo. El
ensayo de DOOM prueba otra parte del sistema: carga externa, ejecucion CPL3,
framebuffer y teclado en QEMU. Su cargador, mapa de RAM y dispositivos
pertenecen al perfil de la VM.

| Orden | Entrega | Evidencia para avanzar |
|---|---|---|
| 1 | Preparar una imagen UEFI removible con el puente y la entrada CASM minima. | Verificar huellas del EFI, del HEX y del paquete; arrancar en QEMU desde la misma imagen y conservar el resultado. |
| 2 | Arrancar esa imagen una vez desde el selector del firmware del equipo. | Registrar placa y version UEFI, modo de arranque, salida de BootServices, entrada CASM y parada observable. Volver a arrancar Windows por su entrada habitual. |
| 3 | Probar los mecanismos de Ring 0 por separado en ese perfil. | Registrar CPU, mapa de RAM, framebuffer y diagnosticos; comprobar pila, excepcion controlada y memoria con permisos. Identificar cada controlador probado. |
| 4 | Arrancar un cliente Rust minimo desde un SBEF externo con el cargador CASM propio. | El kernel mapea RX/R/RW con NX, atiende INVOKE y WAIT y recupera recursos cuando el cliente sale o falla. Repetir con el segundo cliente. |
| 5 | Ampliar al escritorio y los aparatos. | DIRECTOR presenta por CPU y recibe entrada. Disco, audio y otros controladores obtienen evidencia por separado. |

El estado del paso 1 es parcial: Genesis tiene evidencia QEMU con OVMF y
una imagen virtual. Falta preparar la imagen removible de la prueba fisica.
El primer ensayo usa el medio removible para evitar depender de la
particion de Windows. La FAT32 dedicada junto a PERSONAL queda para
despues de verificar el recorrido UEFI y confirmar el destino fisico.

Por cada prueba guardar huellas, configuracion, bytes de entrada, memoria
reservada y el ultimo punto observado. Registrar consola serie si el
equipo la ofrece, o captura del diagnostico visible. Faggin mantiene su
[ruta propia desde reset](../contracts/FAGGIN.md), con la misma entrega
CASM como destino.

| Referencia | Responsabilidad en BMO-X2 |
|---|---|
| TALK-CPU | Puente inicial, entrega de CPU y modelo de etapas Faggin. |
| BMO-X | Lecciones de aislamiento, capacidades y diagnostico. Base de los componentes Rust que se revisen para Ring 3. |
| Ultra-LinuX | Experiencia de escritorio, especialmente espacios y foco, y disciplina de verificacion de builds. |

Los contratos, los artefactos verificados y las pruebas del equipo se
registran en BMO-X2. [Procedencia](../heritage/TRANSFER.md) y
[orden de cierre de Ring 0](RING0-PLAN.md).

## Hitos de la entrada

La base del kernel se escribe desde cero en CASM. BMO-X aporta lecciones y
contratos de referencia; no se ha copiado su kernel Rust a este arbol.

### M0: emision comprobable en el anfitrion

`kernel/boot/entry.casm` es la primera fuente nueva del kernel. Es una sonda
pequena del perfil metal64: imprime un mensaje mediante la tabla de servicios
del cargador y retorna. No configura CPU, memoria o interrupciones.

```powershell
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
```

La orden congela la fuente, produce HEX e IR y ejecuta el verificador antes de
publicar el paquete. Su resultado acredita emision HOST, no una entrada ejecutada
en Ring 0. `metal_puts` requiere la tabla de servicios R15 del contrato metal64;
un salto directo a esos bytes no satisface ese contrato.

### M1: el primer arranque en QEMU

Genesis G1 paso siete casos QEMU/OVMF el 05-11-2026: ejecucion normal con
salida de BootServices, copia exacta del cuerpo, framebuffer esperado, retorno
y CPL=0/HLT=1; cinco rechazos de archivo/paquete y un MapKey invalido con tres
reintentos acotados. Evidencia en `kernel/boot/genesis/evidence/`.
Reproducir con `bmo-x2.ps1 -Accion despertar`.

TALK-CPU ofrece el puente de referencia y evidencia historica de su contexto.
La revision de piezas y condiciones esta en [TRANSFER](../heritage/TRANSFER.md).
La repeticion con Genesis es una prueba nueva conservada aqui; los resultados
anteriores de TALK-CPU no se suman como evidencia del hijo.

1. Fijar la cadena de carga y su contexto: modo de CPU, mapa de memoria,
   framebuffer, pila, tablas de servicios y tratamiento del retorno.
2. Cargar una imagen admitida y llegar a la entrada CASM con ese contexto.
3. Observar el mensaje de diagnostico y una parada controlada del invitado.
4. Rechazar un contexto o imagen incorrectos con un motivo observable.

Antes de llamarlo kernel autonomo, sustituir los servicios provisionales del
cargador por mecanismos propios con sus contratos y pruebas.

### Presupuesto de la entrada Ring 0

La entrada minima propia vive en [kernel/boot/stop](../kernel/boot/stop/README.md).
CASM emite el cuerpo x86-64 en `program.hex` y su IR en `program.ir.json`.
El verificador reconstruye los bytes y aplica el limite antes de publicar
`INICIO.X86`. El limite es estricto, con un maximo de 511 bytes para
el paquete. La cabecera de 24 bytes deja hasta 487 para codigo y datos.
La entrada actual usa 4 bytes de cuerpo y 28 de paquete, con 483 de margen.

El puente UEFI heredado de 12288 bytes pertenece a la cadena de carga.
El presupuesto mide el paquete binario de la entrada, mientras que
`HEX.md` registra aparte el tamano de la representacion de texto.
Las etapas posteriores del kernel tendran su propio presupuesto.

### M2: excepciones y aislamiento

CPU y excepciones primero; despues paginas y permisos. Un #UD controlado debe
dar diagnostico. Mas adelante, el primer programa Rust en Ring 3 pide una
operacion y recibe una respuesta; su fallo termina ese proceso.

Tiempo, planificacion, IPC y drivers tienen nodos reservados con criterios de
aceptacion. Se implementan cuando este recorrido minimo los requiera.

La inspiracion Linux se aplica a separar `arch`, `mm`, `sched`, `ipc` y los
drivers en una estructura navegable. Las decisiones de ABI, capacidades y CASM
siguen siendo propias de BMO-X2. Un solo repositorio combina las piezas y
conserva sus fronteras de privilegio.
