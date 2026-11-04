# Primer hito: una entrada propia y un fallo explicado

La base del kernel se escribe desde cero en CASM. BMO-X aporta lecciones y
contratos de referencia; no se ha copiado su kernel Rust a este arbol.

## M0: emision comprobable en el anfitrion

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

## M1: el primer arranque en QEMU

1. Fijar la cadena de carga y su contexto: modo de CPU, mapa de memoria,
   framebuffer, pila, tablas de servicios y tratamiento del retorno.
2. Cargar una imagen admitida y llegar a la entrada CASM con ese contexto.
3. Observar el mensaje de diagnostico y una parada controlada del invitado.
4. Rechazar un contexto o imagen incorrectos con un motivo observable.

Antes de llamarlo kernel autonomo, sustituir los servicios provisionales del
cargador por mecanismos propios con sus contratos y pruebas.

## M2: excepciones y aislamiento

CPU y excepciones primero; despues paginas y permisos. Un #UD controlado debe
dar diagnostico. Mas adelante, el primer programa Rust en Ring 3 pide una
operacion y recibe una respuesta; su fallo termina ese proceso.

Tiempo, planificacion, IPC y drivers tienen nodos reservados con criterios de
aceptacion. Se implementan cuando este recorrido minimo los requiera.

La inspiracion Linux se aplica a separar `arch`, `mm`, `sched`, `ipc` y los
drivers en una estructura navegable. Las decisiones de ABI, capacidades y CASM
siguen siendo propias de BMO-X2. Un solo repositorio combina las piezas y
conserva sus fronteras de privilegio.
