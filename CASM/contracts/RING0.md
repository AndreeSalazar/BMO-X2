# CASM para el kernel x86-64

CASM se desarrolla para construir el Ring 0 de BMO-X2. Rust queda en Ring 3.
El compilador puede ejecutarse en el anfitrion; su lugar de ejecucion no cambia
el destino de los bytes emitidos. Native se conserva como referencia heredada.

## Que significa HEX preciso

Cada par hexadecimal representa un byte. La salida necesita un perfil declarado,
una fuente congelada, IR, offsets, bytes y comprobacion independiente. Una
operacion desconocida se rechaza; no se completa con bytes aproximados.

El formato HEX no impone un nivel de privilegio. El futuro perfil Ring 0 debe
declarar y comprobar sus precondiciones de CPU, entrada y efectos. El perfil
activo metal64-0.2 sigue siendo una sonda con servicios del cargador: no acredita
por si mismo ejecucion en Ring 0 ni un kernel autonomo.

## Leer la primera entrada

El vector manual de `kernel/boot/fixtures/entry.hex` contiene:

| Offset del cuerpo | Bytes | Lectura del perfil actual |
|---|---|---|
| 0 | 48 8D 35 05 00 00 00 | Direccion del saludo: siguiente instruccion (7) + desplazamiento (5) = 12. |
| 7 | 41 FF 57 10 | Llamada al servicio del cargador mediante R15 + 16. |
| 11 | C3 | Retorno al cargador. |
| 12 | 42 4D 4F ... 0D 0A 00 | Datos: saludo ASCII, salto de linea y cero final. |

Son 48 bytes de cuerpo. El paquete FAGRAW64 agrega 24 de cabecera: 72 en total.
Los bytes de datos y los de instrucciones tienen funciones distintas; mirar
pares hexadecimales sin conocer las regiones no basta para interpretarlos.

`tools/hex_report.py` vuelve a pasar el verificador y contrasta el paquete
completo antes de escribir `HEX.md` en el run. Su tabla muestra linea de fuente,
offset de cuerpo, offset de paquete, clase y bytes. No ejecuta el destino.

## Siguiente frontera del lenguaje

Antes de activar nuevas operaciones, especificar un caso pequeno por capacidad:
funcion sin servicios del cargador, acceso de memoria con ancho definido,
entrada controlada de excepcion y operacion privilegiada requerida por el arranque.
Cada caso exige semantica, IR, vector independiente, emisor, verificador y
negativos. Las pruebas privilegiadas requieren ejecucion aislada en QEMU.
Los estados planeados del catalogo no conceden instrucciones al compilador.
