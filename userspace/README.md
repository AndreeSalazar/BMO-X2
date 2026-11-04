# Userspace: Ring 3 en Rust

Estado: DISENO. Runtime, servicios y aplicaciones se separan del kernel CASM.
No se han creado crates vacios ni se da por disponible `std` del anfitrion.
El runtime minimo requerira un target x86-64 propio, entrada, pila, panico y
ABI de capacidades antes de abrir una ventana o reutilizar servicios mayores.
