# Puente provisional de TALK-CPU

Los cuatro `.hex` y `LEEME.md` se importaron del mismo autor, sin cambiar sus
bytes. Procedencia en `heritage/bridge-origin.json`. `LEEME.md` es historico:
sus rutas y pruebas fisicas se refieren a TALK-CPU, no a esta reconstruccion.

Este puente UEFI entrega contexto RDI, tabla R15 y pila al programa metal64
tras ExitBootServices. La entrada Genesis y sus 22 bytes salen de CASM.
El puente de 12288 bytes sigue siendo codigo manual heredado: no fue generado
por CASM y queda fuera del presupuesto de 512 bytes del paquete Genesis.

El arranque utiliza inicializacion y estado del firmware. No instala aun las
tablas y excepciones propias de BMO-X2 ni constituye un kernel autonomo.
Solo se construyen imagenes virtuales dentro del run; no se instala al PC.

`bmo-x2.ps1 -Accion despertar` compila una fuente congelada nueva, verifica,
prepara FAT32/GPT y ejecuta siete casos con QEMU/OVMF, TCG, un CPU y 256 MiB.
Los scripts del anfitrion se conservan en `tools/boot/`; sus adaptaciones
usan un workspace de salida aislado y el texto GENESIS esperado.
