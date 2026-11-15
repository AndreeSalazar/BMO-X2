# Servicios de driver: frontera propuesta

Estado: DISENO del transporte privilegiado. Biblioteca HID en Ring 3
con pruebas HOST y regresiones QEMU. No hay aun procesos de driver
independientes ni concesion directa de xHCI protegido por IOMMU.

El [perfil declarativo de ULTRA-J](../Ultra-J/README.md#puente-de-registro-de-drivers-en-host)
ya valida y prepara solicitudes desde una carpeta de driver. Declara
identidad PCI, backend SBEF, presupuestos, MMIO, DMA, eventos y
dependencias. Su salida HOST no concede derechos ni inicia procesos.
No cambia el ABI del kernel ni implementa aun el transporte privilegiado.

## Reparto

| Lugar | Trabajo |
|---|---|
| NANO-CORE | Autoridad de propietario, mapeos CPU y DMA, limites y revocacion, recepcion de interrupciones y entrega de eventos autorizados. |
| Driver Ring 3 | Protocolo del dispositivo, descriptores, configuracion, colas y politicas de reintento dentro de los recursos concedidos. |
| Servicio de entrada Ring 3 | Convertir informes HID en teclas, botones y movimiento, distribuirlos segun foco y capacidades. |
| HOST | Construir y verificar el SBEF del servicio, registrar dependencias, recursos solicitados y presupuestos. |

INVOKE y WAIT siguen siendo los puntos de entrada del ABI. Las futuras
operaciones de recurso se definen por contrato antes de asignar numeros.
Este documento no agrega una syscall implementada ni habilita acceso
arbitrario a PCI, puertos de E/S o direcciones fisicas.

## Recursos necesarios

- Una concesion identifica propietario, dispositivo, generacion y
  derechos. Las solicitudes antiguas dejan de valer al revocarla.
- MMIO se limita a las paginas del dispositivo y al espacio del driver,
  sin ejecucion ni acceso desde otras aplicaciones. El acceso a puertos
  de E/S requiere un mecanismo propio acotado; no se concede IOPL global.
- Un buffer DMA fija limites, direccion de acceso y pertenencia. El
  dominio IOMMU y su granularidad real deben comprobarse antes de dar
  control directo al usuario. Si el aislamiento agrupa varios dispositivos,
  la propiedad se concede con esa granularidad o se rechaza el perfil.
- Las interrupciones se asocian a eventos del propietario. WAIT necesita
  resolver la carrera entre observar una cola vacia y quedar dormido.
- La retirada necesita confirmacion de parada o aislamiento efectivo y
  de las invalidaciones antes de borrar o reutilizar los buffers. Una
  respuesta del propio driver no basta para acreditar esa seguridad.

La documentacion [VFIO del kernel Linux](https://docs.kernel.org/driver-api/vfio.html)
explica por que los grupos de aislamiento y DMA importan al conceder
dispositivos a usuario. BMO-X2 debe implementar sus propios mecanismos;
esta referencia no constituye evidencia de que ya esten disponibles.

## Pruebas para declarar terminada la primera entrega

1. Un SBEF de driver inicia en CPL3 con recursos propios; otro proceso
   carece de acceso a sus paginas, MMIO y capacidades.
2. Ambos dispositivos AMD pasan enumeracion y configuracion. El driver
   identifica interfaces desde descriptores y recibe teclado y raton
   simultaneamente, incluyendo liberaciones y modificadores.
3. Accesos CPU y DMA fuera del dominio son rechazados y dejan diagnostico
   sin corrupcion de otro proceso. Se prueban concesiones revocadas.
4. WAIT duerme con colas vacias, despierta por evento y evita perdida de
   notificaciones bajo carga. Se miden latencia, colas llenas y CPU ociosa.
5. Fallar o desconectar el driver retira accesos y libera recursos solo
   tras confirmar revocacion. La siguiente instancia recibe una nueva
   generacion y no consume transferencias antiguas.

Las pruebas actuales de teclado y raton QEMU usan sondas separadas.
La biblioteca compartida y el parser no acreditan aun estos cinco cierres.
