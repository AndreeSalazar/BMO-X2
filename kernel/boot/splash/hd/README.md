# Gato de arranque de mayor resolucion

Perfil `ring0-splash-hd-0.1`. Conserva una region centrada de 256 por
256 pixeles. La mascara crece de 32 por 32 a 64 por 64 celdas. Cada
celda ocupa 4 por 4 pixeles. La silueta parte de las mismas mascaras
de BMO-X, con 56 columnas de dibujo, cuatro de margen a cada lado
y un minimo de dos pixeles de origen por celda.

```powershell
.\bmo-x2.ps1 -Accion gato-hd
```

El cuerpo contiene 219 bytes de codigo, 12 de paleta y 1024 de mascaras.
El paquete total mide 1279 bytes y cabe en la pagina de 4096 bytes que
admite el puente. `-Accion gato` conserva el paquete de 508 bytes.
QEMU usa 1 GiB de RAM virtual y comprueba los tres cuadros.
[Captura](evidence/frame-3.png), [repeticion](evidence/gato.gif)
y [evidencia QEMU](evidence/qemu.json).

El verificador coteja el renderer con `expected-code.hex`, recompone
las mascaras de `main.casm` y registra codigo y datos en `HEX.md`.
El dibujo usa el framebuffer validado que entrega el puente UEFI.
[Contrato Faggin](../../../../contracts/FAGGIN.md).
