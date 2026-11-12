# Primer marco fisico en QEMU

Desde la raiz de BMO-X2 en PowerShell:

```powershell
.\bmo-x2.ps1 -Accion memoria
.\bmo-x2.ps1 -Accion memoria -Cpu Nehalem
$pesos = .\bmo-x2.ps1 -Accion pesos | ConvertFrom-Json
$pesos.Profiles | Format-Table Profile,BodyBytes,HexFileBytes,PacketBytes,VmRamMiB,NormalImageBytes,RunBytes
```

Cada prueba genera un run en `build/CASM` con `program.hex`,
`program.ir.json`, `INICIO.X86`, `HEX.md` y `qemu-results.json`.
El informe de pesos toma la ultima prueba aprobada por perfil y mide
longitudes logicas de archivos. `RunBytes` suma todos los archivos del
run, incluidas las imagenes y capturas. `VmRamMiB` es la capacidad
configurada. `MapConventionalBytes` es la RAM convencional observada
en el mapa de arranque.

## Contrato del ensayo

- El puente UEFI entrega el mapa tras cerrar Boot Services. CASM comprueba
  RDI/RBP, la firma, el estado del cierre y la geometria del mapa.
- El recorrido usa el primer inicio de descriptor convencional elegible,
  alineado a 4 KiB y dentro de 1 a 256 MiB, bajo el mapeo de identidad de
  este entorno QEMU. Excluye las reservas conocidas de codigo y contexto.
- R11 informa el marco y R12 indica si se leyo la marca de ocho bytes.
  El guardian del host verifica la direccion y la marca en memoria fisica.
  El caso con RDI nulo debe detenerse sin escribir la marca.
- El codigo pesa 217 bytes. El paquete FAGRAW64 pesa 241 bytes con cabecera
  de 24 bytes. Quedan 270 bytes bajo el maximo estricto de 511.
- Este perfil es una prueba acotada. El asignador, la devolucion de marcos,
  las tablas propias y la separacion de Ring 3 siguen en el plan.

[Fuente CASM](main.casm) | [Vector independiente](expected.hex) |
[Evidencia QEMU](evidence.json) | [Plan de Ring 0](../../../docs/RING0-PLAN.md)
