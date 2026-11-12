# Revocacion en caliente de una pagina

```powershell
.\bmo-x2.ps1 -Accion revocar
.\bmo-x2.ps1 -Accion revocar -Cpu Nehalem
```

El programa de prueba escribe una marca en la pagina de datos
`0x40002000` desde CPL3. Intenta leer una pagina de supervisor y
provoca el primer #PF. Ring 0 guarda vector, codigo de error, RIP
y CR2 en una entrada fija de 32 bytes. Comprueba la marca,
retira la PTE, ejecuta INVLPG y borra 4096 bytes por su mapa
supervisor. El ensayo reanuda al usuario en la siguiente lectura.

La nueva lectura produce un segundo #PF con error 4, usuario y
pagina ausente. El manejador guarda el segundo registro y limpia
las paginas de codigo y pila. QEMU coteja los dos registros, la
PTE retirada, la pila de Ring 0 y los tres marcos a cero.

| Caso | Codigo hardware | RIP | CR2 |
|---|---:|---|---|
| Lectura de supervisor desde CPL3 | 5 | `0x40000018` | `0x100000` |
| Lectura de pagina revocada desde CPL3 | 4 | `0x4000001A` | `0x40002000` |

El cuerpo mide 930 bytes, el paquete 954 y el diario 64 bytes.
Se usan 36 KiB de la reserva del puente. El ensayo tiene una CPU,
un programa fijo y dos fallos esperados. Para reutilizar un marco
compartido se deben retirar sus mapeos, esperar a que las CPUs
afectadas invaliden sus traducciones y cerrar sus referencias.
Para marcos concedidos a dispositivos tambien se debe retirar
el acceso DMA antes de reutilizar.

[Fuente](main.casm) | [Vector](expected.hex) | [Evidencia](evidence.json)
