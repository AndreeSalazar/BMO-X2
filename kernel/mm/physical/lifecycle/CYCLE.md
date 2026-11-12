# Ciclo de un marco fisico

```powershell
.\bmo-x2.ps1 -Accion marcos
.\bmo-x2.ps1 -Accion marcos -Cpu Nehalem
$pesos = .\bmo-x2.ps1 -Accion pesos | ConvertFrom-Json
$pesos.Profiles | Where-Object Profile -eq ring0-frame-cycle-0.1
```

`boot_frame_cycle()` prueba una sola plaza en Ring 0 con interrupciones
enmascaradas. Usa el primer marco convencional elegible del mapa de
arranque, dentro de la ventana de identidad de la VM de 256 MiB.
R11 conserva la direccion y R13 el propietario actual. Cero significa
libre. Los identificadores 1 y 2 son parte del ensayo.

| Bit en R14 | Transicion comprobada |
|---:|---|
| 0 | El propietario 1 recibe el marco. Se llena la pagina con una marca. |
| 1 | La solicitud del propietario 2 falla por agotamiento. |
| 2 | Se rechaza la devolucion ajena y se comprueban las marcas de los extremos. |
| 3 | El propietario 1 devuelve el marco y se borra la pagina completa. |
| 4 | Se rechaza la segunda devolucion. |
| 5 | El propietario 2 recibe el mismo marco. |

QEMU coteja el descriptor, la direccion fisica, el propietario final, los
seis bits y los 4096 bytes a cero. El caso de RDI nulo conserva a cero
los registros de resultado y carece de la marca de prueba.

El cuerpo mide 474 bytes. El paquete con cabecera mide 498 bytes,
con 13 bytes de margen frente al maximo estricto de 511. El estado
vive en registros durante la prueba y se usa la pila entregada por el
puente. El siguiente paso necesita metadatos de varios marcos y tablas
propias de memoria virtual.

[Fuente CASM](main.casm) | [Vector](expected.hex) | [Evidencia](evidence.json)
