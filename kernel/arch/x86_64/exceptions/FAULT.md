# Primera excepcion propia de BMO-X2

El perfil `ring0-fault-0.1` genera 138 bytes de codigo y un paquete
FAGRAW64 de 162 bytes. La fuente es `main.casm` y el vector de
referencia es `expected.hex`. La IDT y el marco se forman en RAM.

| Offset | Funcion |
|---:|---|
| 0 | Validar la entrega del puente antes de escribir. |
| 32 | Seleccionar la pila y localizar la IDT y el manejador. |
| 53 | Escribir la puerta de interrupcion del vector 6 con el selector CS activo. |
| 97 | Instalar IDTR. La base es contexto + 0x14000 y el limite es 111. |
| 122 | Ejecutar UD2 y provocar #UD. |
| 126 | Leer RIP guardado en RDX y registrar el vector 6 en EAX. |
| 135 | Detener la CPU. El rechazo de la entrega tambien llega aqui. |

El banco comprueba la puerta activa y los 40 bytes del marco observado
en la pila. El RIP registrado coincide con el offset 122 del cuerpo.
Con RDI nulo, la copia de prueba del puente permite comprobar que
RSP conserva el valor de entrega y la pagina de la IDT queda intacta.
Se usa la reserva del puente y su selector de codigo. La tabla solo instala el vector 6,
con interrupciones enmascaradas y parada terminal. Las otras excepciones,
la recuperacion y las transiciones a Ring 3 requieren pruebas propias.

```powershell
.\bmo-x2.ps1 -Accion excepcion
```

Se conserva el HEX, la IR, el informe por rangos y las observaciones
de QEMU en el run. [Intel SDM, referencia de UD2](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf).

El mismo paquete paso los dos casos en `qemu64` y `Nehalem`.
[Evidencia QEMU](evidence.json).
