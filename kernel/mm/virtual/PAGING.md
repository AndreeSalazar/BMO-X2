# Primer CR3 propio en QEMU

```powershell
.\bmo-x2.ps1 -Accion paginacion
.\bmo-x2.ps1 -Accion paginacion -Cpu Nehalem
$pesos = .\bmo-x2.ps1 -Accion pesos | ConvertFrom-Json
$pesos.Profiles | Where-Object Profile -eq ring0-paging-0.1
```

CASM toma el primer bloque elegible de seis marcos de 4 KiB en el mapa
convencional de UEFI, tras ExitBootServices. El bloque completo queda
entre 1 MiB y 256 MiB y fuera de las reservas de codigo y contexto.
Se limpian los seis marcos y se emplean cinco para tablas y uno para
los datos de la prueba.

- Mapeo de identidad de los primeros 256 MiB con paginas de 2 MiB
  para supervisor. Conserva el acceso al codigo y a la pila entregada.
- Una pagina de datos en `0x40000000` con permiso de usuario, solo
  lectura y NX. CASM activa CR0.WP y EFER.NXE, y lee la marca por
  esa direccion despues de cargar CR3.
- QEMU coteja CR3, las cinco tablas fisicas, la reserva, los registros
  y la marca. El caso de contexto nulo conserva el CR3 heredado.

El ensayo usa un nucleo virtual, 256 MiB y el modo de cuatro niveles
con NX. Conserva la pila del puente y termina en CPL0. El acceso a
la pagina desde CPL3 y las excepciones de proteccion pertenecen al
siguiente ensayo. Este mapa de identidad es transitorio y no aplica
permisos W^X a las paginas de supervisor.

El cuerpo mide 473 bytes, el paquete FAGRAW64 mide 497 bytes y quedan
14 bytes frente al maximo estricto de 511. Las tablas ocupan 20 KiB
y el marco de datos ocupa 4 KiB.

[Fuente CASM](main.casm) | [Vector](expected.hex) | [Evidencia](evidence.json)
