# Estado de la base BMO-X2 -- 04-11-2026

## Transporte USB AMD -- 15-11-2026

La cuarta foto confirma dos puertos conectados en metal con el censo
en marcha y la espera fija. La nueva sonda usa debounce por puerto,
termina con >=100 ms estables observados y tiene limite de 1 segundo.
QEMU termina el caso conectado en 110 ms. HOST pasa diez secuencias
del helper ensamblado. QEMU pasa tambien ausencia de puertos y fallo
PIT con parada y revocacion. Pendiente confirmar el tiempo adaptativo
en AMD y enumerar ambos HID. Esta fase sigue siendo sincrona de arranque.

La tercera foto confirma `XHCI DMA OK` en AMD y cero puertos al cerrar
la sonda. La siguiente version alimenta puertos que lo requieren,
espera 200 ms medidos por PIT canal 2 y registra CCS antes de detener
el xHC. QEMU comprueba el censo activo y el fallo sin PIT con salida
acotada, parada y Bus Master revocado. Falta repetir el censo en metal.

La segunda foto muestra `XHCI DMA MAPA` y tres puertos conectados.
Se corrigio una restriccion del prototipo que exigia RTSOFF/DBOFF
a partir de 4096. El padre documenta RTSOFF 0x4C0 en esta placa.
El validador admite bancos compactos sin solapamientos y agrega
pruebas HOST de su codigo ensamblado. Pendiente repetir en metal.

El BOOTLOG V3 del equipo registra AMD 1022:149C en 2B:00.3,
BAR 0xFC200000. La foto confirma el reinicio del controlador y la
espera PS/2. La entrada USB fisica permanece pendiente.

La sonda aislada de transporte agrega No Op, lectura de RTSOFF/DBOFF,
colas DMA verificadas, consumo de cambios de puerto y parada con
revocacion de Bus Master. QEMU TCG con 256 MiB pasa el transporte y el
rechazo W+X. Las pruebas HID QEMU separadas conservan teclado y raton.
El controlador de esta sonda se ensambla desde .inc mediante Clang;
todavia no procede del emisor CASM. La puerta Ring 0 mide 1034 B,
el driver va aparte en el puente UEFI. No es un sistema de 2 KiB.
[Evidencia y limites](../kernel/drivers/bus/evidence/transport-qemu.json).

## Compatibilidad del lanzador -- 05-11-2026

Se sustituyo `System.IO.Path.GetRelativePath`, ausente en .NET Framework de
Windows PowerShell 5.1, por rutas relativas acotadas al proyecto. Siete casos
de nombres y rechazos pasan en 5.1 y 7. El build registra PowerShell/CLR y el
generador de imagen usa el mismo PowerShell del llamador.
La ejecucion completa desde 5.1 paso los siete casos QEMU, con el generador
de disco tambien en 5.1; `environment.json` conserva la version observada.
El banco CASM paso 107/108 (una omision Linux), ocho pruebas de catalogo y
11 invariantes. El cuerpo y el paquete Genesis mantienen 22 y 46 bytes.

## Genesis G1 -- ejecucion QEMU observada el 05-11-2026

- Siete casos QEMU/OVMF aprobados con Genesis generado por CASM: salida de
  BootServices, copia exacta de 22 bytes, texto GENESIS en framebuffer,
  retorno y estado CPL=0/HLT=1; cinco rechazos de archivo/paquete y fallo
  inyectado de MapKey con tres reintentos acotados.
- Paquete: 46 bytes. Puente UEFI heredado: 12288 bytes. VM: 256 MiB, TCG,
  qemu64, un CPU. No son medidas de energia ni memoria minima necesaria.
- Evidencia revisada en `kernel/boot/genesis/evidence/`; imagenes y volcados
  completos en el run bajo `build/CASM/`. `-Accion despertar` reproduce y
  conserva el resultado. Los comandos no instalan entradas de arranque.
- El puente es HEX manual de TALK-CPU con procedencia y hash. El nuevo kernel
  CASM aun necesita excepciones, memoria y mecanismos propios: no es autonomo.

## Genesis G0 -- 05-11-2026

Revision visual de SUPER GRAFO: tarjetas con texto contenido, conexiones de
arbol desviadas alrededor de nodos y fijacion de posiciones visibles. Editor
de estilo con motivo y guardado tras 500 ms de pausa. Ciudad distingue formas
estables por archivo y admite forma manual; color/forma no mueven parcelas.
14 pruebas de grafo y 61 de aplicacion pasan (una medicion omitida). Las formas
anaden 4 bytes por instancia GPU (44 -> 48); no cambia el HEX de Genesis.

- Fuente propia `kernel/boot/genesis/main.casm`: salida GENESIS por el servicio
  metal64 y retorno. Vector manual de 22 bytes; paquete FAGRAW64 de 46 bytes.
- `tools/genesis.py` exige fuente exacta, verificador, vector y presupuesto
  estricto de menos de 512 bytes incluyendo cabecera. Registro HOST persistido
  en `kernel/boot/genesis/host.json`; no hay ejecucion ni arranque observado.
- Tres pruebas Genesis cubren alteraciones, limites y conservacion del grafo.
  Doce pruebas del grafo y el banco de la aplicacion SG (60, una medicion
  ignorada) pasan con el soporte nuevo de colores con motivo y direccion local.
- `super-grafo/genesis.json` fija once nodos del recorrido visual. El catalogo
  general tiene 61 responsabilidades y 105 relaciones. La disposicion y los
  tintes se guardan en esta carpeta, sin desplazar archivos reales.

## Revision de maduracion -- 05-11-2026

- 61 nodos y 105 relaciones tipadas; lexer, simbolos, enteros, parser, tipos y
  almacenamiento tienen implementaciones separadas y notas de SUPER GRAFO.
- Modelo de compilacion HOST: 1.077.280 -> 361.648 bytes, ahorro de 715.632
  bytes (66,43 %). No es una medida de RSS o del kernel; la semilla ejecutable
  crece 512 bytes (180.736 -> 181.248) con las mismas herramientas y flags.
- 333 casos (279 admitidos, 54 rechazados) coinciden con `d2575a8` en HEX,
  IR, paquete, stdout y stderr. No se ejecuta el codigo de destino.
- El banco metal64 conserva 107 aprobados y una omision Windows declarada.
  El banco del almacenamiento cubre 11 invariantes. La cache pasa tres pruebas;
  la cuarta exige enlaces Linux y queda omitida explicitamente.
- Una lista `CASM/sources.json` alimenta builds Windows y Linux, con todas sus
  cabeceras registradas. El build Linux y sus sanitizadores siguen pendientes.
- Resumen y huellas en [host-maturity.json](../CASM/metrics/host-maturity.json).
  Metodo y limites en [CONTROL-PERFORMANCE-ELEGANCE](../CASM/CONTROL-PERFORMANCE-ELEGANCE.md).

## Listas y jerarquia ejecutable -- 05-11-2026

- `CASM/catalog.json`: 45 elementos del lenguaje y su pipeline; 37 del perfil
  activo, uno parcial y siete planeados. Son nodos declarativos, no porcentajes.
- Ocho tipos generan la tabla C. El verificador conserva su tabla independiente;
  tres patrones x86-64 se contrastan con el vector manual de entrada.
- Ocho pruebas del catalogo pasan, junto al banco metal64 y las 11 invariantes.
  Los 333 casos diferenciales siguen identicos tras introducir el generador.
- SUPER GRAFO lee los modulos y las condiciones originales. Taller revisado
  visualmente con el arbol, los estados, fuentes y tipos desplegables.
- Cuatro pruebas puras CASM de SUPER GRAFO y cuatro pruebas nuevas de plataforma
  pasan; la prueba del repositorio Linux original no se aplica a este checkout.
  Consultas reales de resumen, tipos, codificaciones, regla y mapa contrastadas.
- El mapa exige la fuente congelada, reconstruye IR/HEX y contrasta cabecera y
  cuerpo del paquete y los campos basicos del reporte. No autentica el reporte
  ni sustituye la verificacion semantica. Entrada: 48 bytes de cuerpo, 72 de paquete.
- Detalles y comandos en [CASM/CATALOG](../CASM/CATALOG.md).

Lo que sigue conserva las cifras y el alcance del primer commit del 04-11.

## Lo hecho aqui

- 38 archivos CASM importados del mismo autor, con commit y SHA-256 de origen.
- 35 nodos de responsabilidad, 49 relaciones tipadas y notas visibles por ruta
  en SUPER GRAFO. Las relaciones de plan no son llamadas de codigo.
- Distribucion inicial compacta por familias, con posiciones de detalle guardadas.
- Herramientas Windows para construir, comprobar, emitir HEX y consultar SG.
- Estructura en ingles: CASM, kernel y userspace; CPU en kernel/arch/x86_64.
- Primera fuente nueva kernel/boot/entry.casm: emision HOST de 48 bytes de
  cuerpo y paquete verificado de 72 bytes; usa servicios del cargador metal64.
- Perfil CASM x86-64: 16 necesidades, con dos heredadas, seis parciales y
  ocho pendientes; son estados del inventario, no porcentajes de terminacion.
- SUPER GRAFO actual compilado desde sus fuentes, con `--offline --locked`;
  salida en `build/tools/super-grafo`. El ejecutable previo del proyecto
  vecino no tenia la consulta `guardar` que sus fuentes ya implementaban.

## Comprobaciones observadas en este anfitrion

| Comprobacion | Resultado y limite |
|---|---|
| Clang 23.1.2, C11, -Wall -Wextra -Werror -pedantic | Semilla metal64 construida sin avisos. Es una herramienta host, no el backend de CASM. |
| Banco metal64 | 107 aprobadas de 108; HOST-MEMORY omitida porque Windows no ofrece RLIMIT_DATA. |
| Saludo de oro | Paquete de 64 bytes; cuerpo de 40 bytes; SHA-256 b3fd9814bcce6881f9cf3ad10b299d759f4f5b801a6526c59131a4d1c84e4b33. |
| Entrada propia | Vector independiente igual al HEX y al cuerpo del paquete: 48/72 bytes; SHA-256 del paquete 57df0033b3a4a9cbeb5e31a458b5fc0fbb4aa24432aafde3468c9714de2b1534. |
| Publicador PowerShell | Fuente valida genera HEX/IR/paquete; uint8_t=256 rechaza con INT-OVERFLOW sin publicar INICIO.X86. |
| Guardian del catalogo | Rechaza seis mutaciones: otro destino, ruta externa, estado desconocido, nodo ausente, Rust en Ring 0 y ciclo. |
| CASM Native | La fuente completa coincide con cuerpo y runtime al regenerarla en memoria; no se ejecutaron generaciones ELF Linux aqui. |
| SUPER GRAFO | Consultas reales resumen, guardar y nota aprobadas; 23 dependencias de codigo y cero ciclos detectados en esta base. Esto no prueba ausencia de errores semanticos. |
| Revision visual | Grafo abierto y revisado. Se sustituyo el despliegue inicial de todos los archivos por familias cerradas para facilitar la lectura. |
| Scripts | Sintaxis Python y PowerShell comprobada. |

Los informes y fuentes congeladas de cada intento estan en `build/CASM/`.
Una compilacion rechazada tambien conserva su run, con el motivo, sin paquete.
Los documentos heredados conservan sus resultados Linux/QEMU anteriores;
no se atribuyen al kernel BMO-X2.

## Lo siguiente

La apertura de SUPER GRAFO se corrigio: `--grafo` delante de la carpeta se
interpretaba como ruta. El parser acepta ambas posiciones y el lanzador abre
ahora `BMO-X2.sg-workspace`. La definicion fija raiz/vista/panel; la sesion local
conserva subcarpeta, vista, panel y pestanas guardadas. Hay acciones de establecer,
guardar, abrir y reabrir el ultimo espacio. No se ejecutan procesos al restaurar.
El banco de la aplicacion paso 60 pruebas; una medicion esta ignorada.

Concretar C1 de [CASM-ROADMAP](CASM-ROADMAP.md): lenguaje y perfil de destino del
kernel, tomando funciones/bucles/buffers de la experiencia Native y el contrato
de emision/verificacion de metal64. El reparto del frontend y la lectura de
reglas distribuidas en SUPER GRAFO ya estan hechos; la siguiente capacidad
requiere semantica, IR, emision, verificador y pruebas antes de activarse.

Las operaciones privilegiadas, los subsistemas del kernel y el runtime Rust
siguen en DISENO; la sonda de entrada esta compilada en HOST.
Genesis ya se ejecuto en QEMU mediante el puente provisional. No se ha
arrancado un kernel BMO-X2 autonomo ni esta entrega en el Ryzen; no se desplego
a discos. No se aplico el parche incompleto 0.3.
