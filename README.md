# BMO-X2

Hijo de BMO-X. Kernel x86-64 escrito en CASM, runtime y servicios propios
de Ring 3 en Rust, y SUPER GRAFO como mesa de trabajo.
Autor: Eddi Salazar, Lima, Peru.

BMO-X2 arranca perfiles de prueba independientes en QEMU/OVMF. Ya hay
evidencia de ejecucion en Ring 0 y Ring 3, admision de un SBEF embebido,
una llamada INVOKE y revocacion de paginas. La siguiente integracion
es cargar un SBEF externo y ejecutar el primer cliente Rust.

## Probar en QEMU

Desde la raiz de BMO-X2, con QEMU, Clang y Python disponibles:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bmo-x2.ps1 -Accion gato-hd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1
```

El primer comando compila el perfil y verifica tres cuadros sin ventana.
El segundo abre el ultimo ensayo aprobado en una ventana QEMU y lo deja
visible. Se puede indicar `-Run .\build\CASM\run-...` para abrir otra
prueba aprobada. El visor usa un snapshot del disco virtual y una copia
de las variables UEFI.

![Cuadro final del gato de arranque en QEMU](kernel/boot/splash/hd/evidence/frame-3.png)

El puente UEFI entrega el framebuffer al perfil CASM tras cerrar
Boot Services. El gato se dibuja como una silueta de 64 por 64 celdas,
ampliadas a 256 por 256 pixeles. Se muestran tres cuadros y la CPU
queda detenida en el ultimo. El escritorio y los atajos de espacios
de trabajo pertenecen al servicio de Ring 3 previsto.
[Detalle grafico](kernel/boot/splash/hd/README.md) |
[Diseno del escritorio](userspace/services/desktop/WORKSPACES.md)

## Avances comprobados

Los pesos de la tabla son bytes de cuerpo y de paquete binario
FAGRAW64. La cabecera mide 24 bytes. El limite de menos de 512 bytes
se aplica a los perfiles de entrada compacta. Las demostraciones mas
grandes usan el limite de 4096 bytes del puente.

| Accion | Cuerpo / paquete | Resultado en QEMU |
|---|---:|---|
| `despertar` | 22 / 46 B | Genesis sale de Boot Services, escribe en pantalla y retorna. [Evidencia](kernel/boot/genesis/evidence/qemu.json) |
| `parada` | 4 / 28 B | Detencion propia en CPL0. [Evidencia](kernel/boot/stop/evidence/qemu.json) |
| `detectar` | 8 / 32 B | CPUID hoja 0 y perfil de CPU observado. |
| `pila` | 50 / 74 B | Seleccion de pila y rechazo de contexto nulo. [Evidencia](kernel/boot/context/evidence.json) |
| `excepcion` | 138 / 162 B | IDT minima y captura de #UD. [Guia](kernel/arch/x86_64/exceptions/FAULT.md) |
| `memoria` | 217 / 241 B | Seleccion y prueba de un marco de 4 KiB. [Evidencia](kernel/mm/physical/evidence.json) |
| `marcos` | 474 / 498 B | Propiedad, agotamiento, devolucion, borrado y reutilizacion de un marco. [Evidencia](kernel/mm/physical/lifecycle/evidence.json) |
| `paginacion` | 473 / 497 B | CR3 propio y alias de usuario de solo lectura y NX. [Evidencia](kernel/mm/virtual/evidence.json) |
| `aislamiento` | 716 / 740 B | Ejecucion en CPL3, #PF de proteccion y borrado de 8 KiB. [Evidencia](kernel/mm/user/evidence.json) |
| `abi` | 1239 / 1263 B | SBEF embebido, INVOKE por SYSCALL y rechazos de ABI ajeno y W+X. WAIT responde -4. [Evidencia](kernel/syscalls/evidence.json) |
| `revocar` | 930 / 954 B | Revoca una pagina, reanuda CPL3 y registra el siguiente #PF. [Evidencia](kernel/mm/virtual/revoke/evidence.json) |
| `gato` / `gato-hd` | 484 / 508 B y 1255 / 1279 B | Tres cuadros verificados. [Evidencia HD](kernel/boot/splash/hd/evidence/qemu.json) |

`-Accion pesos` informa los bytes de codigo, HEX de texto, paquete,
imagenes y ejecucion completa. Las VM usan 256 MiB en las pruebas
del kernel y 1024 MiB en las del gato. La prueba de revocacion usa
36 KiB dentro de la reserva del puente. Los valores de la VM
indican capacidad configurada. La RAM residente del kernel integrado
queda por medir.

En HOST, CASM conserva el resultado de 333 casos diferenciales
frente a la base. SUPER GRAFO registra 124 nodos, 233 relaciones
y 57 elementos del catalogo CASM.
[Medidas CASM](CASM/CONTROL-PERFORMANCE-ELEGANCE.md) |
[Estado del compilador](CASM/STATUS-BMO-X2.md) |
[Catalogo de nodos](super-grafo/CATALOG.md)

## Responsabilidades

| Lugar | Trabajo |
|---|---|
| [CASM](CASM/STATUS-BMO-X2.md) | Fuente, IR, emision x86-64, HEX exacto y verificacion independiente. |
| [kernel](kernel/README.md) | Ring 0 en CASM. Arranque, CPU, memoria, aislamiento, admision SBEF y capacidades. |
| [userspace](userspace/README.md) | Rust como lenguaje principal del runtime, supervisor, servicios y escritorio de Ring 3. |
| [contracts](contracts/README.md) | ABI, SBEF y fronteras de arranque y ejecucion. |
| [heritage](heritage/README.md) | Procedencia y revision de 110 paquetes Cargo del padre. |
| [tools](tools/README.md) | Build, empaquetado SBEF, diagnostico y pruebas HOST y QEMU. |
| [super-grafo](super-grafo/README.md) | Nodos, dependencias, evidencia y criterios de cierre. |

Rust llevara la base propia de Ring 3. El supervisor decide como
arrancar y recuperar servicios con las capacidades que reciba.
Ring 0 conserva la autoridad sobre memoria, admision y operaciones
privilegiadas. Las aplicaciones de C, C++ y otros lenguajes entran
cuando su binario y runtime cumplen el mismo ABI y SBEF. Python
requiere un interprete portado a Ring 3 que abra los scripts como datos.
[El nucleo de escritorio](userspace/services/desktop/WORKSPACES.md) ya
compone superficies y procesa los atajos de cuatro espacios en pruebas HOST.
Su ejecutable Rust freestanding ya se empaqueta como SBEF ABI 1.
En Windows, `tools/view-desktop.ps1` abre una vista previa interactiva
de los cuatro espacios usando el compositor Rust.
[Reglas de Ring 3](userspace/POLICY.md) |
[Frontera de ejecucion](docs/RING-BOUNDARY.md)

El [ensayo DOOM](userspace/apps/doom/README.md) compila DoomGeneric con GCC,
empaqueta su ELF64 como SBEF ABI 1 y arranca E1M1 en CPL3 tras la intro
del gato. QEMU comprueba el menu y el desplazamiento por teclado.
El [mezclador de audio Rust](userspace/services/audio/AUDIO.md) prueba
PCM, volumen y medicion en HOST. La salida virtual y USB quedan pendientes.

## Siguientes entregas

1. **Carga externa.** El cargador CASM valida un SBEF producido por el
   toolchain, mapea sus regiones con permisos y ejecuta la entrada.
   Se prueba una imagen admitida y los rechazos comparados con el lector HOST.
2. **Escritorio Rust en Ring 3.** QEMU ya prueba la sesion interactiva con
   composicion por CPU, teclado y espacios en el perfil de ensayo.
   Queda integrarla con el cargador CASM propio y recuperar sus recursos
   al cerrar el proceso.
3. **Ciclo de vida y ABI.** WAIT debe bloquear y despertar por senal o
   plazo. Se prueba reutilizar marcos en un segundo proceso antes de
   fijar el ABI. SMP y DMA requieren confirmacion de revocacion antes
   de reutilizar memoria compartida.
4. **Arranque fisico de prueba.** El primer hito es entrar en Ring 0
   desde el EFI separado en el volumen A: y registrar una parada controlada.
   La FAT32 dedicada junto a PERSONAL es un paso posterior.
   [Orden y evidencia de arranque](docs/FIRST-BOOT.md).

[Plan de Ring 0](docs/RING0-PLAN.md) |
[ABI 1](contracts/ABI.md) |
[Cargador SBEF](contracts/SBEF-LOADER.md) |
[Inventario del padre](heritage/RING3-CRATES.md) |
[Arranque Faggin](contracts/FAGGIN.md)

## Trabajar en el repositorio

```powershell
.\bmo-x2.ps1 -Accion abrir
.\bmo-x2.ps1 -Accion resumen
.\bmo-x2.ps1 -Accion consultar -Consulta nota -Argumentos '{"ruta":"CASM/x86_64"}'
.\bmo-x2.ps1 -Accion mapa
.\bmo-x2.ps1 -Accion comprobar
.\bmo-x2.ps1 -Accion medir
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
.\bmo-x2.ps1 -Accion preparar-grafo
```

El workspace `BMO-X2.sg-workspace` guarda la raiz portable, la vista
Grafo y el Taller CASM. SUPER GRAFO conserva su sesion local y las
posiciones versionadas en `super-grafo/orden.json`. Los ejecutables
HOST y resultados reproducibles viven en `build/`. Se pueden indicar
rutas de herramientas mediante `-Python`, `-Compiler` y `-SuperGrafo`.

El [estado historico](docs/STATUS.md) conserva Genesis y las primeras
medidas del compilador. [Ruta de CASM](docs/CASM-ROADMAP.md) |
[Licencia de la base CASM](heritage/COPYING-CASM)
