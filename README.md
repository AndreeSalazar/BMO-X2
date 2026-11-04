# BMO-X2

Hijo de BMO-X: reconstruir el kernel x86-64 con CASM en Ring 0, Rust en
Ring 3 y SUPER GRAFO como mesa de trabajo. Autor: Eddi Salazar, Lima, Peru.

**Base del primer commit, 04-11-2026:** CASM con procedencia, 35 nodos y una
primera entrada propia compilada y verificada en host. Todavia no hay un
kernel BMO-X2 arrancable. [Estado y evidencia](docs/STATUS.md).

## Una base combinada, tres responsabilidades

```text
BMO-X2/
  CASM/                         lenguaje, emisor y verificador del anfitrion
    src/                        semilla metal64 existente
    native/                     experiencia de autocompilacion en CASM
    x86_64/                     perfil estrategico requerido por el kernel
    contracts/                  precision de HEX, IR y comprobacion
  kernel/                       Ring 0 propio, escrito desde cero en CASM
    boot/entry.casm             primera sonda de emision; aun sin arranque
    arch/x86_64/                CPU, exceptions e interrupts
    init/                       orden de inicializacion
    mm/                         memoria y aislamiento
    capabilities/               autoridad concedida
    syscalls/                   puerta a Ring 3
    time/  sched/  ipc/          tiempo, ejecucion y comunicacion
    drivers/                    mecanismos de dispositivos
  userspace/                    Ring 3 en Rust
    runtime/  services/  apps/
  contracts/                    frontera entre las piezas
  heritage/                     procedencia y lecciones de BMO-X
  tools/                        construccion y comprobacion
  super-grafo/                  nodos, notas, posiciones y mapa
```

La inspiracion Linux se toma como separacion de subsistemas. La base de CPU,
el lenguaje CASM, la puerta y sus capacidades tienen contratos propios. Los
nodos aun no implementados contienen su responsabilidad y prueba de cierre.

## Entrar al proyecto

```powershell
.\bmo-x2.ps1 -Accion abrir       # SUPER GRAFO, con la organizacion del proyecto
.\bmo-x2.ps1 -Accion resumen     # consulta real a SUPER GRAFO
.\bmo-x2.ps1 -Accion consultar -Consulta nota -Argumentos '{"ruta":"CASM/x86_64"}'
.\bmo-x2.ps1 -Accion mapa        # regenera mapa, notas y posiciones
.\bmo-x2.ps1 -Accion comprobar   # contratos de nodos + banco CASM metal64
.\bmo-x2.ps1 -Accion compilar    # ejemplo -> .hex + IR -> verificacion -> paquete
.\bmo-x2.ps1 -Accion compilar -Source .\kernel\boot\entry.casm
.\bmo-x2.ps1 -Accion preparar-grafo # construye SG local si el ejecutable esta anticuado
```

Los ejecutables de SUPER GRAFO, Clang y Python son herramientas del anfitrion.
La entrada PowerShell de construccion se usa con PowerShell 7.
Se pueden indicar sus rutas con `-SuperGrafo`, `-Compiler` y `-Python`.
La copia actual de SG se construye en `build/tools/super-grafo`, desde
las fuentes del proyecto vecino, en modo offline y sin modificarlas.
Si existe el cache local anterior al cambio de nombres, se reutiliza como
alternativa. Los ejecutables y resultados de build no forman parte del commit.

## Donde vive cada cosa

| Nodo | Trabajo |
|---|---|
| [CASM](CASM/STATUS-BMO-X2.md) | Lenguaje propio, emisor x86-64, HEX exacto y verificadores. |
| [kernel](kernel/README.md) | Futuro Ring 0 en CASM: arranque, CPU, excepciones, memoria, capacidades y puerta. |
| [userspace](userspace/README.md) | Futuro Ring 3 en Rust: runtime, servicios y aplicaciones. |
| [contracts](contracts/README.md) | Frontera versionada entre capas; todavia sin ABI de BMO-X2 implementado. |
| [heritage](heritage/README.md) | Procedencia de CASM y aprendizajes que se toman de BMO-X. |
| [super-grafo](super-grafo/README.md) | Nodos, notas, posiciones y mapa consultable. |
| [tools](tools/README.md) | Comprobar la estructura, construir y verificar sin escribir discos. |

Primero leer [la ruta de CASM](docs/CASM-ROADMAP.md) y el
[catalogo de nodos](super-grafo/CATALOG.md). Cada nodo declara que existe,
que falta, de quien depende y con que prueba se acepta.
El alcance inicial esta en [FIRST-BOOT](docs/FIRST-BOOT.md). Las 16 necesidades
del lenguaje para el kernel estan en [requirements.json](CASM/x86_64/requirements.json).

## Las decisiones de esta reconstruccion

- Solo destino x86-64: corresponde al hardware y a la evidencia disponibles.
  Otra arquitectura requiere un proyecto y pruebas propios.
- CASM emite sus propios bytes. Clang/GCC pueden construir una semilla del
  anfitrion; no generan los bytes del programa CASM.
- El `.hex` es representacion exacta de bytes, no una garantia por si mismo.
  Fuente congelada, IR, bytes, comprobacion independiente y huellas viajan juntos.
- Ring 0 se construye en CASM; Rust se reserva a Ring 3. El arranque y las
  entradas privilegiadas que CASM aun no puede expresar son trabajo pendiente.
- Se distingue HEREDADO, HOST y DISENO. Una prueba host no acredita QEMU ni metal.
- La organizacion por nodos sigue responsabilidades reales. No se crean crates
  Rust vacios para aparentar que el compilador CASM ya esta implementado en ellos.

La base CASM importada conserva sus avisos y la copia de licencia en
[heritage/COPYING-CASM](heritage/COPYING-CASM). BMO-X y los otros proyectos
permanecen como referencias separadas; el trabajo nuevo se hace aqui.
