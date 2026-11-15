# Huella de BMO-X2 con ULTRA-J

El ensayo `run-desktop-media-2ad81add6e32` arranca desde FAT32,
muestra el escritorio, abre el panel ULTRA-J con doble clic,
ejecuta ACTION.UJB y vuelve al mismo espacio con Super + Q.
Paso en QEMU con 256 MiB asignados al invitado. El ensayo anterior
uso 1024 MiB. Quedan por medir el minimo de arranque y el uso total
de RAM en el invitado y en metal.

| Componente | Medida |
|---|---:|
| Puente UEFI | 20480 B |
| Paquete INICIO.X86 | 3448 B |
| Puerta de sesion Ring 0, incluida en INICIO.X86 | 999 B |
| SBEF del escritorio y del presentador ULTRA-J | 9625 B |
| Accion externa ACTION.UJB | 23 B |
| Cuatro archivos de arranque | 33576 B (32,79 KiB) |
| Imagen de disco GPT/FAT32 de prueba | 68174336 B (65,02 MiB) |
| Regiones del cliente Ring 3 | 16 KiB mapeados |
| Pila Ring 3 | 4 KiB mapeados |
| Filas visibles del framebuffer VGA, 1280 x 800 a 4 B por pixel | 4096000 B (3,91 MiB) |

La imagen de disco incluye la capacidad del volumen. Las paginas de
Ring 3 incluyen relleno y se cuentan aparte del framebuffer VGA.
El total de memoria debe incluir el puente, el contexto, las tablas,
el mapa de memoria y las reservas para dispositivos. La puerta de
999 B es el componente al que corresponde el presupuesto de 2 KiB.

## Referencias de escritorio

| Sistema | RAM | Disco | Que mide |
|---|---:|---:|---|
| BMO-X2 con ULTRA-J | 256 MiB | 65,02 MiB | Configuracion QEMU validada e imagen del ensayo. |
| Ubuntu Desktop 26.04 LTS | 6 GB | 25 GB libres | Requisitos publicados por Canonical para un uso comodo. [Notas de Ubuntu](https://documentation.ubuntu.com/release-notes/26.04/) |
| Windows 11 | 4 GB | 64 GB | Requisitos de Microsoft. [Requisitos de Windows](https://support.microsoft.com/en-us/windows/experience/compatibility/windows-11-system-requirements) |
| Mac mini M4 (2024) con macOS | 16 GB | SSD de 256 GB | Configuracion base del equipo. [Ficha de Apple](https://support.apple.com/en-gb/121555) |

La tabla pone en contexto el alcance del prototipo. Para comparar
consumo entre sistemas se necesita una misma tarea, resolucion y
criterio de medicion. Medir escritorio en reposo, aplicacion abierta,
aplicacion cerrada y otro ciclo de apertura permite separar memoria
base, pico y recursos recuperados.

Los siguientes costes a registrar son marcos y tablas de Ring 0,
memoria por ventana de DIRECTOR y bytes copiados por cuadro. Para
entrada y pantalla conviene medir del evento hasta el cuadro
presentado con el mismo recorrido en cada sistema.

Para repetir el ensayo del lanzador, seguir
[los comandos de ULTRA-J](../Ultra-J/README.md#desde-el-icono-del-escritorio)
y agregar `--ram-mib 256` al comando de stage. `qemu-results.json`
registra RAM asignada, tamano de imagen, suma de archivos y framebuffer.
