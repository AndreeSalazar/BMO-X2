# Ensayo CASM de ABI 1

CASM emite el codigo privilegiado y un SBEF de 168 bytes con una
region RX, integrado en el vector. El guardia de Ring 0 coteja la
cabecera y la region del ensayo antes de copiar el codigo a su
pagina de usuario. QEMU ejecuta el programa en CPL3, observa tres
entradas SYSCALL y verifica el fallo de proteccion y la limpieza.

El programa verifica la respuesta de INVOKE, el rechazo de una
capacidad invalida y el estado provisional de WAIT antes de
provocar #PF. En las copias QEMU se cambia el ABI o el permiso RX
por W+X, con el checksum exterior actualizado. CASM detiene el
ensayo con CR3 heredado, paginas de usuario a cero y cero llamadas.
El lector HOST reporta los offsets 6 y 52 respectivamente.

El cuerpo CASM mide 1239 bytes y el paquete 1263. La prueba usa
32 KiB dentro de la reserva existente del puente. El paquete
compacto de entrada mantiene su limite menor de 512 bytes.
Quedan por probar el cargador de imagenes externas, la espera
real y el cliente producido por toolchain dentro de la VM.

[Contrato de registros](../../contracts/ABI.md) | [Vector](expected.hex) |
[Evidencia](evidence.json)
