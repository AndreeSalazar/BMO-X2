# Drivers de Ring 3

Los protocolos de dispositivo, descriptores y adaptacion de entrada
pertenecen a servicios de usuario. El NANO-CORE conserva concesion,
proteccion, notificacion y revocacion de recursos privilegiados.

`usb/` contiene el primer modulo Rust `no_std` y sin `unsafe` de esta
familia. Es una biblioteca utilizada por el escritorio, no un proceso
independiente con acceso directo al controlador. La separacion de
procesos y el transporte xHCI de usuario siguen pendientes.

[Contrato propuesto y pruebas de cierre](../../contracts/DRIVER-SERVICES.md)

ULTRA-J ofrece un [registro declarativo en HOST](../../Ultra-J/README.md#puente-de-registro-de-drivers-en-host)
con `new driver`, `driver check` y `driver prepare`. Cada carpeta
declara un backend real y sus recursos; la preparacion no equivale
a cargar un driver ni conceder MMIO o DMA.
