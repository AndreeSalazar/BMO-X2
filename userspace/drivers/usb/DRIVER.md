# USB en Ring 3: estado y frontera

## Codigo que ya vive aqui

| Archivo | Responsabilidad | Evidencia |
|---|---|---|
| `src/hid.rs` | Decodificar informes boot de teclado y raton, cambios de modificadores y liberacion al desconectar. | Pruebas HOST; el escritorio usa el mismo fuente en sus sondas USB QEMU. |
| `src/descriptor.rs` | Leer una configuracion acotada y descubrir interfaces HID boot con sus endpoints IN. Generar los paquetes de solicitud SET_CONFIGURATION y SET_PROTOCOL. | HOST con descriptores reales capturados en las sondas QEMU de teclado y raton. |
| `src/input.rs` | Servicio de entrada con fuentes separadas, cola acotada, cambios atomicos y desconexion con liberacion. | HOST y ejecucion CPL3 en las sondas QEMU de teclado y raton, por separado. Desconexion del servicio comprobada solo en HOST. |
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
   El resultado actual en metal acredita No Op y dos puertos conectados.
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
