# USB xHCI conectado al escritorio RmlUi

`--usb both` agrega el perfil con dos dispositivos USB2 directos, con
registros MMIO dinamicos y buffers separados. QEMU verifica ambos a la
vez sin PS/2, la revocacion al parar y la salida segura con puertos vacios.
El candidato experimental AMD esta instalado en las rutas existentes de
A:, con respaldo verificado. [Evidencia](../Reports/rmlui-usb-dual.json).
La prueba fisica de teclado y raton sigue pendiente. Conectarlos antes
de arrancar; el estado superior muestra K, M, fase y CC. F12 detiene
el controlador; la recuperacion de entrada requiere reiniciar.

El puntero comienza centrado y aparece desde el primer cuadro, incluso
si USB esta detenido. La foto del primer ensayo AMD mostro K:OK, M:OK
y fase 210. Esa compilacion mostraba el CC anterior a la transferencia
fallida. El transporte ahora registra el CC de la transferencia cotejada
y distingue identidad (211), transferencia (212) y puerto (213).
K y M indican configuracion; USB ON indica que el controlador sigue activo.
El raton del perfil conjunto reserva el tamano maximo anunciado por su
endpoint. Solicita protocolo Report y lee su descriptor HID. Ring 3
usa el ID, la longitud y los campos declarados para separar el giro de
la rueda, los tres botones y los ejes relativos de hasta 16 bits. Cada
informe actualiza solo los campos que declara. Los campos usados deben caber en los
primeros ocho bytes y el informe debe contener todos los bytes declarados.
Si el formato queda fuera de ese perfil, se registra el rechazo.
Este cambio sigue el precedente de BMO-X en `uhid/src/formato.rs`.

Una segunda prueba AMD mostro USB ON y movimiento del puntero, con
latencia alta. Al mover el puntero, el escritorio
restaura los pixeles bajo la flecha y compone su nueva posicion sin
rasterizar RmlUi. Las acciones que modifican el documento dibujan la escena.
El recorrido abarca el escritorio logico de 1280x800 y sus margenes
dependen del GOP.

## Cursor y presentacion por regiones

El escritorio nativo cambia el color de la flecha al pasar sobre un
boton o al pulsar el primario. La flecha conserva su punto activo y el
mismo recorrido de entrada. Entrar y salir del boton usa las mismas
cajas del puntero, sin volver a rasterizar el documento.

BMO-X guarda los pixeles bajo el cursor en DIRECTOR (`scene/cursor.rs`).
Su presentador de software agrupa hasta ocho cajas modificadas en
`sin_gpu/sucio.rs` y fusiona dos cuando el area extra compensa el coste
de la copia. Linux DRM/KMS ofrece regiones modificadas mediante
`FB_DAMAGE_CLIPS` y un plano de cursor segun el controlador. Wayland
separa la superficie del cursor de la aplicacion y fija su punto activo.
[DRM/KMS](https://docs.kernel.org/gpu/drm-kms.html),
[protocolo Wayland](https://wayland.freedesktop.org/docs/html/apa.html).

El perfil USB conjunto presenta por separado la caja anterior y la
nueva, recortadas al escritorio. A escala 1, la copia completa
escribe 4096000 bytes. Dos cajas de 12x17 escriben como maximo 1632
bytes, unas 2510 veces menos datos para ese movimiento. Esta relacion
mide volumen, no tiempo ni fotogramas. Conservar las cajas separadas
evita que un salto largo convierta el area intermedia en escrituras GOP.

Ring 3 conserva la composicion y el punto activo. INVOKE 10 valida
limites, paso de fila, formato y escala antes de copiar cada caja.
Los modos con otra escala usan la presentacion completa de INVOKE 9.
La latencia fisica del puntero y del resaltado sigue pendiente de medir
en AMD.

El perfil reserva 57344 bytes DMA y dos paginas de codigo supervisor.
No cubre hubs, reconexion automatica ni aislamiento IOMMU. Las notas
siguientes sobre perfiles separados describen las sondas anteriores.

## Evidencia actual

El escritorio nativo ya recibe informes xHCI reales en QEMU. Hay dos
perfiles separados: teclado USB con raton PS/2 y raton USB con teclado
PS/2. La alternativa PS/2 del dispositivo probado se descarta en el
invitado, por lo que no puede aprobar la prueba por esa otra entrada.

- Teclado: 36 informes en el run final; Enter, espacios, Super+Q y reapertura.
- Raton: tres informes de movimiento, pulsacion y liberacion; accion
  ULTRA-J visible en la superficie RmlUi.
- Ambos conservan rechazo W+X antes de copiar codigo y lectura del SBEF
  desde FAT32 mediante UEFI. No se inyecta el SBEF con un loader QEMU.
- El dibujador necesita mas tiempo por cuadro bajo TCG. La prueba espera
  hasta 90 segundos por presentacion; sigue exigiendo el resultado visual.

Ver [evidencia conservada](../Reports/rmlui-usb-qemu.json).

## Frontera efectiva

`usb_input.rs` enlaza InputService y los decoders Rust usados por las
sondas anteriores. Entrega scancodes con prefijos y movimiento firmado
a la misma politica DIRECTOR y al mismo contexto RmlUi de Ring 3.
El propietario es unico y las llamadas C son sincronicas; no retienen
punteros del llamador ni conceden acceso a hardware.

Se reutiliza provisionalmente el backend de diagnostico de un dispositivo
en `xhci_command_probe.inc`. Ese backend configura y mantiene el anillo
en Ring 0 y entrega un informe escalar mediante INVOKE. La nueva maquina
Activation/PendingActivation de Ring 3 no controla aun esa configuracion.
No es todavia el driver final aislado de usuario ni una prueba de IOMMU.

UEFI reserva diez paginas LoaderData (40960 bytes) para DMA; el transporte
comprueba su propiedad, limites y separacion del usuario. Los alias MMIO
son supervisores y NX. La prueba del raton vuelve a comprobar los bits
de mapeo y la reserva desde QEMU. El servicio no recibe direcciones DMA.
Esto no constituye aislamiento frente a un dispositivo DMA malicioso.

La puerta de sesion ocupa 1584 bytes. La etapa de controlador ocupa
4067 bytes en teclado y 4096 en raton, en su pagina reservada aparte.
INICIO.X86 ocupa 3785 bytes y no excede su limite de 4096. El SBEF de
cada perfil ocupa 1852246 bytes. El coste del controlador no desaparece
por estar separado de la puerta. El pico de heap RmlUi permanece en
3050544 bytes y el framebuffer en 4096000 bytes; no son toda la RAM.

## Probar en PowerShell 5.1

Desde BMO-X2, con las herramientas LLVM, Rust y QEMU ya usadas:

```powershell
$bmoPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $bmoPython -B tools/desktop/rmlui/native/guest.py --desktop --usb keyboard
& $bmoPython -B tools/desktop/rmlui/native/media.py build/CASM/run-20261112-174958-944cb997 build/CASM/run-20261112-045636-c461240e --usb keyboard
```

Usar `--usb mouse` en ambos comandos para el otro perfil. El segundo
comando genera y prueba el run. Para abrir el ultimo aprobado de cada tipo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-usb-keyboard
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\boot\view.ps1 -Profile rmlui-usb-mouse
```

## Limites de las sondas anteriores

Los perfiles son QEMU-only: el backend vivo actual acepta el xHCI
emulado con su geometria conocida. `deploy.ps1` rechaza su instalacion
en A:; el escritorio fisico confirmado se conserva.

Para AMD falta unir el transporte dinamico ya usado en la sonda EP0
con esta ruta viva, conservando MPS aprendido, tamanos de contexto,
RTSOFF/DBOFF y terminaciones. Despues deben coexistir teclado y raton
con slots/anillos separados y retirada segura ante desconexion o error.
La parada/revocacion de una sesion de este escritorio permanente y la
reconexion fisica aun no estan probadas. No dar este estado por USB
HID terminado en METAL ni usar la prueba de un dispositivo como prueba
de dos a la vez.
