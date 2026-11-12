# Userspace: Ring 3 en Rust

Estado: DISENO. Runtime, servicios y aplicaciones se separan del kernel CASM.
El [supervisor](supervisor/README.md) organizara el inicio, la configuracion
y la recuperacion de los servicios con las capacidades que reciba.
[Reglas de Ring 3](POLICY.md) y [espacios de trabajo](services/desktop/WORKSPACES.md).
No se han creado crates vacios ni se da por disponible `std` del anfitrion.
El runtime minimo requerira un target x86-64 propio, entrada, pila, panico y
ABI de capacidades antes de abrir una ventana o reutilizar servicios mayores.

El runtime Rust de BMO-X es el candidato de herencia, con cuatro dependencias
locales que deben auditarse. Las fuentes actuales exponen INVOKE y WAIT;
channel_kick entra como operacion de canal. La transferencia requiere el
contrato de puerta y de imagen del nuevo kernel CASM. Ver
[heritage/TRANSFER](../heritage/TRANSFER.md); no se ha copiado codigo aun.
