# Userspace: Ring 3 en Rust

Rust es el lenguaje principal del runtime, el supervisor y los servicios
propios de Ring 3. El [supervisor](supervisor/README.md) organizara el
inicio, la configuracion y la recuperacion de los servicios con las
capacidades que reciba. CASM conserva la autoridad de Ring 0.
[Reglas de Ring 3](POLICY.md) y [espacios de trabajo](services/desktop/WORKSPACES.md).

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
