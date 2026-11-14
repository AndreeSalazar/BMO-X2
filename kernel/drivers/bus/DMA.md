# Prestamo y revocacion de DMA

El contrato previsto entrega al servicio una capacidad de transferencia.
Ring 0 vincula dispositivo, direccion DMA, permiso de lectura o escritura,
rango y propietario. El mapeo de IOMMU queda
acotado a los marcos concedidos. La CPU y el dispositivo tienen
traducciones independientes.

| Paso | Condicion para avanzar |
|---|---|
| Conceder | Validar dispositivo, capacidad, rango y direccion. Reservar los marcos y mapearlos en el dominio IOMMU. |
| Transferir | La cola acepta solo referencias a prestamos activos. El dispositivo confirma la finalizacion. |
| Cerrar | Detener nuevas solicitudes y confirmar la finalizacion o una parada efectiva del dispositivo. |
| Revocar | Retirar el mapeo DMA y confirmar las invalidaciones pertinentes. Retirar los mapeos CPU que pierden acceso y confirmar sus invalidaciones. |
| Reutilizar | Con todos los accesos cerrados, borrar si cambia el propietario y devolver al asignador. |

Si falla la confirmacion, el buffer sigue reservado y el diagnostico
registra el dispositivo y la fase. Si el equipo carece de aislamiento
DMA verificable, la ruta directa queda fuera del perfil de usuario.

La primera prueba pendiente usara un dispositivo virtual y un buffer.
Debe demostrar transferencia permitida, rechazo fuera del rango y
retencion del buffer cuando la revocacion queda sin confirmar. El
ensayo actual de revocacion de pagina cubre el TLB de una CPU.

El puente del escritorio reserva cinco paginas contiguas de EfiLoaderData
por debajo de 256 MiB y las entrega en los campos B8/C0 del contexto.
La variante QEMU de comandos agrega una pagina para contextos
y cuatro para scratchpads (40 KiB en total). Ring 0 valida toda la reserva y prepara
una tabla de direcciones fisicas alineadas. Publica la tabla en
DCBAA[0] solo si HCSPARAMS2 solicita scratchpads y aborta antes de
activar el controlador si solicita mas de cuatro.
El run `run-desktop-media-1c740af27864` comprueba 20480 bytes a cero,
la cobertura por el mapa UEFI y la separacion del contexto y el codigo.
El perfil normal conserva la reserva en blanco. La variante
`stage_desktop_media.py --xhci-command` usa esa reserva con qemu-xhci
para un comando No Op y coteja el TRB de finalizacion. Comprueba parada,
restauracion del registro PCI Command y retiro de las paginas MMIO.
Con un usb-kbd emulado tambien restablece el puerto, asigna una ranura,
direcciona el dispositivo y lee su descriptor de 18 bytes por EP0.
La misma sonda lee la configuracion de 34 bytes, valida una interfaz
HID boot, solicita SET_CONFIGURATION y SET_PROTOCOL y configura
el endpoint 1 IN. QEMU inyecta F2 y F3, con sus flancos de liberacion.
La sonda rearma cuatro posiciones fijas y verifica el retorno al
inicio de las colas de transferencias y de eventos con veinte informes.
WAIT comprueba el evento al despertar del PIT. INVOKE valida el TRB
y entrega el informe a Rust. QEMU comprueba que CABINA abre con el
controlador activo y que este se detiene tras el vigesimo informe.
La etapa se guarda bajo `qemu-only`. Antes de programar las colas,
Ring 0 exige que las diez paginas tengan cobertura exclusiva de
EfiLoaderData y esten separadas del contexto, del paquete y del SBEF.
Si la parada no se confirma, la sonda
intenta desactivar bus mastering y conserva las paginas reservadas.

La comprobacion acota las direcciones que el controlador recibe del
driver. La proteccion frente a un dispositivo que accede fuera de
esas direcciones requiere que el hardware aplique un dominio IOMMU.
El contrato comun de prestamos define propiedad, direccion y
revocacion. AMD IOMMU e Intel VT-d son posibles implementaciones
de ese contrato. Quedan pendientes esos dominios, las transferencias
continuas de teclado y la enumeracion del raton.

QEMU pide cero scratchpads. La prueba coteja las cuatro direcciones
de la tabla, las paginas a cero y DCBAA[0] a cero. Queda probar el uso
real de scratchpads. Los desplazamientos de los contextos se
calculan con el tamano anunciado. QEMU ejercita el formato de 32
bytes con teclado full-speed y high-speed. Queda validar 64 bytes
con un controlador que anuncie ese formato.

[Revocacion de pagina](../../mm/virtual/revoke/HOT-UNMAP.md) |
[Referencia de DMA en Linux](https://docs.kernel.org/core-api/dma-api-howto.html)
