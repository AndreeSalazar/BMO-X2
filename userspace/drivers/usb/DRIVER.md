# USB en Ring 3: estado y frontera

## Codigo que ya vive aqui

| Archivo | Responsabilidad | Evidencia |
|---|---|---|
| `src/hid.rs` | Decodificar informes boot de teclado y raton, cambios de modificadores y liberacion al desconectar. | Pruebas HOST; el escritorio usa el mismo fuente en sus sondas USB QEMU. |
| `src/descriptor.rs` | Leer una configuracion acotada y descubrir interfaces HID boot con sus endpoints IN. Generar los paquetes de solicitud SET_CONFIGURATION y SET_PROTOCOL. | HOST con descriptores reales capturados en las sondas QEMU de teclado y raton. |
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
builds `rustc` freestanding actuales. Cambiar de carpeta no crea una
frontera de memoria: este perfil sigue enlazado con la sesion actual.

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
