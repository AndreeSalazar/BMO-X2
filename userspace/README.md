# Userspace: Ring 3 en Rust

Rust es el lenguaje principal del runtime, el supervisor y los servicios
propios de Ring 3. El [supervisor](supervisor/README.md) organizara el
inicio, la configuracion y la recuperacion de los servicios con las
capacidades que reciba. CASM conserva la autoridad de Ring 0.
[Reglas de Ring 3](POLICY.md) y [espacios de trabajo](services/desktop/WORKSPACES.md).

## Orden de trabajo y presupuestos

| Orden | Elemento | Base para comparar | Prueba de cierre en BMO-X2 |
|---|---|---|---|
| 1 | Runtime y supervisor | Inicio de sesion, dependencias y recuperacion de servicios | Cerrar una aplicacion, revocar sus capacidades y reutilizar sus paginas para otra. |
| 2 | Entrada y configuracion | Distribucion de teclado, atajos, foco y velocidad del puntero | F2, movimiento, clic y reconexion desde USB. Guardar las preferencias de sesion. |
| 3 | DIRECTOR y CABINA | Espacios de Ultra-LinuX, cambio de ventana y diagnostico de BMO-X | Abrir y cerrar clientes con foco propio y medir los recursos que devuelve cada uno. |
| 4 | Archivos y aplicaciones | Lanzador, acceso a archivos y configuracion persistente | Abrir un SBEF desde disco con las capacidades solicitadas. Cargar el IWAD y ejecutar DOOM. |
| 5 | Audio y servicios opcionales | Mezclador, volumen por aplicacion y dispositivos | Reproducir efectos y musica, medir latencia y liberar los buffers al cerrar. |

Linux y Windows sirven como referencia de comportamiento para el
usuario. BMO-X aporta bibliotecas y contratos para revisar. El
supervisor delega capacidades concretas y cada servicio conserva sus
dependencias y presupuesto.

El recorrido de codigo es fuente Rust, C o C++ a ELF64 x86-64, luego
HOST empaqueta SBEF y Ring 0 valida y mapea sus regiones. Un volcado
`.hex` permite inspeccionar los mismos bytes. El presupuesto de
2 KiB pertenece al paquete minimo, y cada SBEF del escritorio o de
una aplicacion tiene su propio limite.

Para optimizar una pieza, registrar bytes SBEF, paginas mapeadas,
pila, buffers, coste en reposo y memoria devuelta al cerrar. Comparar
el mismo comportamiento antes y despues. El perfil actual del
escritorio usa 8958 bytes SBEF y 20 KiB de regiones y pila.
[Presupuestos HOST](../contracts/SBEF-HOST.md).

El primer hito de Rust es un cliente `no_std` para x86-64 que arranque
desde SBEF, haga INVOKE y termine de forma que el kernel recupere sus
recursos. Luego se adapta el runtime del padre y se prueba un servicio.
Las aplicaciones C y C++ pueden usar el ABI y el empaquetado SBEF.
Otros lenguajes necesitan sus runtimes portados al mismo entorno.

Rust tambien puede enlazar bibliotecas maduras en C dentro de Ring 3.
El componente Rust mantiene la politica del servicio y llama a C por
una interfaz FFI con tipos, tamanos y propiedad de memoria definidos.
Un wrapper revisa las precondiciones de la llamada. Una biblioteca
enlazada comparte el espacio de memoria del proceso. El primer
escritorio usa componentes enlazados y llamadas directas.
[Interoperabilidad Rust y C](https://doc.rust-lang.org/nomicon/ffi.html)

El nucleo de escritorio ya pasa sus pruebas HOST de foco y composicion.
En el modelo de Meta-Kernel de BMO-X2, ese nucleo toma las decisiones de
sesion y pantalla en CPL3. Ring 0 conserva la autoridad sobre las
capacidades y los dispositivos.
[Escritorio y prueba HOST](services/desktop/WORKSPACES.md)

El runtime Rust de BMO-X es el candidato de herencia, con cuatro dependencias
locales que deben auditarse. Las fuentes actuales exponen INVOKE y WAIT;
channel_kick entra como operacion de canal. La transferencia requiere el
contrato de puerta y de imagen del nuevo kernel CASM. Ver
[heritage/TRANSFER](../heritage/TRANSFER.md); no se ha copiado codigo aun.
