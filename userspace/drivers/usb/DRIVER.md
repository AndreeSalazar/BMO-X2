# USB en Ring 3: estado y frontera

## Codigo que ya vive aqui

| Archivo | Responsabilidad | Evidencia |
|---|---|---|
| `src/hid.rs` | Decodificar informes boot de teclado y raton, cambios de modificadores y liberacion al desconectar. | Pruebas HOST; el escritorio usa el mismo fuente en sus sondas USB QEMU. |
| `src/descriptor.rs` | Leer una configuracion acotada y descubrir interfaces HID boot con sus endpoints IN. Generar los paquetes de solicitud SET_CONFIGURATION y SET_PROTOCOL. | HOST con descriptores reales capturados en las sondas QEMU de teclado y raton. |
| `src/input.rs` | Servicio de entrada con fuentes separadas, cola acotada, cambios atomicos y desconexion con liberacion. | HOST y ejecucion CPL3 en las sondas QEMU de teclado y raton, por separado. Desconexion del servicio comprobada solo en HOST. |
| `src/activation.rs` | Secuenciar SET_CONFIGURATION, SET_PROTOCOL de cada interfaz y Configure Endpoint; exigir terminaciones del propietario y plazos en microsegundos. | HOST, incluidas interfaz compuesta, respuesta antigua, STALL, residual y expiracion. No conectado aun al transporte del escritorio RmlUi. |
| `src/xhci.rs` | Admitir endpoint USB2 interrupt IN y calcular DCI, intervalo y campos de contexto sin direcciones DMA. | HOST; validacion de todos los bInterval FS/LS, HS y endpoint 15. |
| `src/tests.rs` | Rechazos con offset, dispositivo compuesto, alternates, truncamientos, descriptores HID y mutaciones. | HOST. No sustituye enumeracion en hardware. |

El parser no supone interface cero ni endpoint 0x81. Conserva el numero
de cada interface y admite teclado y raton en la misma configuracion.
El perfil selecciona alternate cero, endpoints interrupt IN con paquetes
de hasta 64 B y configuraciones de hasta 4096 B. El transporte debera
validar tambien velocidad e intervalos segun el controlador. HID de
protocolo report, hubs, dispositivos que no ofrecen boot y alternates
que requieren seleccion explicita necesitan perfiles adicionales.

El desktop conserva `usb_hid.rs` como adaptador de su politica de atajos.
Comparte `hid.rs` mediante una referencia de fuente para mantener los
builds `rustc` freestanding actuales. Las sondas `tools/desktop/usb_probe.rs`
y `usb_mouse_probe.rs` enlazan la biblioteca USB y pasan los reportes del
transporte mediado por `InputService`, antes de adaptarlos al escritorio.
Cambiar de carpeta no crea una frontera de memoria: este perfil sigue
enlazado con la sesion actual.

En QEMU el teclado procesa 260 informes y cruza el anillo de transferencias;
el raton verifica movimiento firmado, pulsacion y liberacion. Ambos abren
CABINA, esperan sin trabajo y cierran la sesion deteniendo el controlador.
Son perfiles separados de un dispositivo cada uno. Las sondas USB omiten
el icono y panel F3 de configuracion para mantener el limite de codigo RX
de 8192 B; el escritorio normal los conserva. El teclado usa 7552 B RX y
un SBEF de 9733 B; el raton usa 6624 B RX y un SBEF de 8702 B. Cada perfil
mapea 16384 B para sus regiones, mas 4096 B de pila; los buffers DMA de
la sonda (40960 B) son un coste separado. No son el consumo del sistema.

`InputService<DEVICES, EVENTS>` combina fuentes de teclado y raton en
una cola fija. Un informe que no cabe devuelve `Backpressure` sin
modificar el decoder ni publicar parte de sus eventos. El llamador debe
conservar el informe para reintentar; no puede descartarlo ni reutilizar
su buffer de transporte por esa respuesta. Al desconectar se retiran
eventos pendientes de la fuente y se publican liberaciones y `Detached`.
Si no hay espacio para cerrar, la fuente permanece activa hasta drenar
la cola y reintentar. La siguiente vinculacion usa otra generacion.

Estos tokens son identificadores locales de biblioteca, no capacidades
del NANO-CORE. No conceden acceso a hardware ni sustituyen la revocacion
de DMA. El servicio es de un solo propietario; el transporte concurrente
necesita sincronizacion y eventos del ABI. El codigo se compila para
x86-64 sin std, pero no existe todavia un SBEF independiente de este
servicio ni una ruta xHCI de usuario que lo alimente durante el arranque.
Las sondas actuales reciben informes mediante INVOKE desde el transporte
de diagnostico Ring 0. Aun no notifican desconexion fisica a `detach` ni
prueban reconexion en QEMU. Esas operaciones siguen pendientes en el ABI
del transporte, aunque la biblioteca ya verifica su comportamiento HOST.

## Lo que queda antes de entrada USB fisica

1. Enumerar ambos dispositivos y leer sus descriptores EP0 en el AMD.
   La sonda METAL ya acredita descriptores del primer dispositivo;
   no acredita configuracion HID ni dos dispositivos activos a la vez.
2. Integrar un transporte de driver Ring 3 con concesiones de dispositivo,
   MMIO y buffers DMA y con revocacion comprobada. El contrato actual
   exige IOMMU para conceder DMA directo a un driver de usuario.
3. Ejecutar las solicitudes de configuracion, comprobar sus terminaciones
   y crear los endpoints para ambas interfaces. Emitir una solicitud no
   acredita que el dispositivo la haya aceptado.
4. Recibir transferencias de teclado y raton a la vez, informar errores,
   dormir sin trabajo y rearmar solo las colas del propietario vigente.
5. Cerrar el servicio, retirar accesos y comprobar desconexion, reconexion
   y recuperacion sin tocar memoria de otra sesion.

La sonda ASM bajo `kernel/drivers/bus/` sigue siendo diagnostico y
referencia de transporte. Todavia contiene enumeracion xHCI en Ring 0
para QEMU. No se declara como arquitectura final de driver ni como una
implementacion de aislamiento DMA mediante IOMMU.

## Activacion Ring 3, sin confundir peticion con exito

`Activation<N>` prepara primero SET_CONFIGURATION y luego SET_PROTOCOL
para cada numero de interfaz real. Despues solicita Configure Endpoint
con la mascara de contextos descubierta. Ready solo se alcanza tras
confirmar todas las terminaciones; una peticion emitida no cambia a Ready.
El transporte autorizado debe comprobar TRB, slot, endpoint y propietario
antes de entregar esa terminacion. Los identificadores locales del modulo
no sustituyen esa comprobacion ni conceden MMIO/DMA.

Una terminacion con error o plazo vencido bloquea la activacion. No se
libera ni reutiliza DMA desde este modulo: el transporte debe confirmar
la parada y revocacion. Un teclado compuesto conserva cada interfaz y
cada endpoint; no se supone que todo sea interfaz cero y endpoint 0x81.
Los contextos producidos dejan el puntero de dequeue a cero: solo el
transporte puede completarlo con un anillo reservado y autorizado.

La secuencia tiene pruebas HOST y compila sin std para x86-64, pero no
esta enlazada a INVOKE ni al arranque del escritorio nativo. Por tanto,
este cambio por si solo no resuelve teclado/raton USB en METAL.
Los campos siguen la [especificacion xHCI 1.2, seccion 6.2.3](https://cdrdv2-public.intel.com/625472/625472_xHCI_Rev1_2b.pdf).

## Comprobacion HOST

Desde BMO-X2 en PowerShell 5.1:

```powershell
New-Item -ItemType Directory -Force build/usb-ring3 | Out-Null
rustc --edition=2024 -D warnings --test userspace/drivers/usb/src/lib.rs -o build/usb-ring3/tests.exe
if ($LASTEXITCODE -ne 0) { throw 'Fallo el build del banco USB.' }
& .\build\usb-ring3\tests.exe
rustc --edition=2024 --target x86_64-unknown-none -D warnings --crate-type rlib --crate-name bmo_x2_usb -C panic=abort -C opt-level=s userspace/drivers/usb/src/lib.rs -o build/usb-ring3/libbmo_x2_usb.rlib
```

Las muestras de `fixtures/` conservan su run de procedencia y SHA-256.
La [definicion USB HID 1.11](https://www.usb.org/sites/default/files/hid1_11.pdf)
define los perfiles boot de teclado y raton y la solicitud SET_PROTOCOL.
