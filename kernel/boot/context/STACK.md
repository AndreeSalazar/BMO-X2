# Primera pila de BMO-X2

Perfil `ring0-context-0.1`. CASM emite 50 bytes de codigo. El paquete
FAGRAW64 ocupa 74 bytes y deja 437 de margen bajo el limite de entrada.
La fuente es `main.casm`. El vector manual es `expected.hex`.

| Offset | Bytes | Motivo |
|---:|---:|---|
| 0 | 6 | Enmascarar interrupciones, conservar el RSP recibido en RSI e iniciar estado de rechazo en EAX. |
| 6 | 5 | Comparar RDI con el RBP entregado por el puente antes de leer memoria. |
| 11 | 15 | Comprobar la firma `METAL64!` en el contexto. |
| 26 | 6 | Exigir que ExitBootServices haya concluido. |
| 32 | 13 | Seleccionar el tope de la pila, escribir una marca con PUSH y recuperarla con POP. |
| 45 | 2 | Marcar aceptacion en EAX. |
| 47 | 3 | Detener la CPU. Las tres ramas de rechazo llegan al mismo HLT sin cambiar RSP. |

La reserva de 32 paginas del puente sigue siendo la fuente de memoria.
El puente usa `[contexto+0x1000, contexto+0x11000)` para el mapa y
`[contexto+0x11000, contexto+0x12001)` para la lectura del paquete.
Su pila inicial baja desde `contexto+0x20000`. Este perfil terminal
usa la pagina `[contexto+0x13000, contexto+0x14000)` y deja alineado
RSP tras PUSH y POP. QEMU comprueba el mapa, ambas direcciones de pila
y la escritura de la marca dentro de la pagina.

El rechazo se prueba con RDI nulo en una copia del puente dentro de
la VM. La firma, RBP y las reservas del puente conservan el contrato.
El caso negativo exige que RSP quede donde estaba y la pagina quede
intacta. El perfil depende de un RBP valido entregado por el puente.
La validacion general de mapeos, la pagina de guarda y el manejo de
excepciones requieren las tablas propias en una entrega posterior.

```powershell
.\bmo-x2.ps1 -Accion pila
```

El run guarda el HEX, la IR, el paquete, el desglose por instruccion
en `HEX.md` y las dos observaciones en `qemu-results.json`.

Los casos normal y de rechazo pasaron con el mismo paquete en
`qemu64` y `Nehalem`, con distintas direcciones de entrega.
[Evidencia QEMU](evidence.json).
