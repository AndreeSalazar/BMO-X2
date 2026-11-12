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

El runtime Rust de BMO-X es el candidato de herencia, con cuatro dependencias
locales que deben auditarse. Las fuentes actuales exponen INVOKE y WAIT;
channel_kick entra como operacion de canal. La transferencia requiere el
contrato de puerta y de imagen del nuevo kernel CASM. Ver
[heritage/TRANSFER](../heritage/TRANSFER.md); no se ha copiado codigo aun.
