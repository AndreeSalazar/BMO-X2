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
El run `run-desktop-media-1c740af27864` comprueba 20480 bytes a cero,
la cobertura por el mapa UEFI y la separacion del contexto y el codigo.
La reserva permanece en blanco. Falta vincularla a las colas de xHCI
y verificar la primera finalizacion de un comando del controlador.

[Revocacion de pagina](../../mm/virtual/revoke/HOT-UNMAP.md) |
[Referencia de DMA en Linux](https://docs.kernel.org/core-api/dma-api-howto.html)
