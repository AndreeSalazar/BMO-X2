# Gato de arranque de BMO-X2

Demostracion de Ring 0 en QEMU. El modulo CASM dibuja el gato en el
framebuffer RGB/BGR de 32 bits validado y entregado por el puente UEFI.
El contorno es claro y los ojos recorren tres intensidades cian.
La CPU queda detenida con el ultimo cuadro visible.

```powershell
.\bmo-x2.ps1 -Accion gato
```

El banco crea una imagen FAT32/GPT en el run y arranca QEMU con
1024 MiB de RAM virtual. La imagen virtual usa cerca de 65 MiB de
espacio logico. El banco verifica los tres cuadros completos, el
paquete cargado y la parada en CPL0. Los tres PNG de QEMU y el
informe quedan bajo `build/CASM/run-.../`. El ensayo no requiere
preparar un volumen fisico.

[Captura final](evidence/frame-3.png), [repeticion de los tres cuadros](evidence/gato.gif)
y [registro de QEMU](evidence/qemu.json). La repeticion usa tiempos
ilustrativos entre las capturas.

| Offset del cuerpo | Bytes | Funcion |
|---:|---:|---|
| 0 | 24 | Bloquear interrupciones enmascarables y comprobar la entrega RDI/RBP y ExitBootServices. |
| 24 | 53 | Centrar la region y localizar las mascaras con RIP relativo. |
| 77 | 24 | Seleccionar el color de los ojos y el orden RGB/BGR. |
| 101 | 68 | Dibujar 32 por 32 celdas a escala 8. |
| 169 | 44 | Registrar el cuadro, espaciar el pulso con TSC y acotar la espera. |
| 213 | 3 | Parada propia. |
| 216 | 12 | Paleta de tres colores. |
| 228 | 256 | Dos mascaras de 1 bit por celda, contorno y ojos. |

El cuerpo ocupa 484 bytes y el paquete con cabecera ocupa 508. El
guardian independiente contrasta la plantilla de codigo con el
vector de referencia y vuelve a empaquetar las celdas de la fuente.
Las esperas usan el contador TSC con un limite de iteraciones. La
duracion exacta depende del invitado y la carga de la VM.

La silueta se redujo de las mascaras `TRAZO` y `OJOS` de
`Ultra_kernel_x86-64/kernel/src/ring0/core/gato/masks.rs` de BMO-X
en la revision `6076bdefefc67877419ca53633c6e40cb45fc92d`.
La fuente `main.casm` conserva las celdas del dibujo reducido.
La reduccion usa 28 por 32 celdas, dos columnas vacias a cada lado
y un minimo de tres pixeles de origen por celda. El ojo tiene prioridad
si ambos planos coinciden.
`expected-code.hex` se cotejo con un ensamblado x86-64 de referencia.
En cada build, CASM emite el codigo y empaqueta las mascaras.

La prueba grafica y las pruebas de pila son perfiles separados.
El arranque integrado, las tablas de memoria y la IDT propia
siguen el [plan de Ring 0](../../../docs/RING0-PLAN.md).
