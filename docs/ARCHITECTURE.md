# Arquitectura inicial de BMO-X2

Decision del propietario, 04-11-2026: reconstruir mejor el kernel de BMO-X
mediante nodos; CASM emite HEX preciso x86-64 para Ring 0 y Rust vive en Ring 3.
Las tres ramas son `CASM/`, `kernel/` y `userspace/`; toda carpeta nueva usa
nombres en ingles. `super-grafo/` conserva los nombres de archivo requeridos
por la herramienta. El snapshot historico CASM conserva su procedencia exacta.

```text
CASM del anfitrion
  fuente -> analisis -> IR -> codificador x86-64 -> HEX
                            comprobacion independiente -> imagen admitida

CPU x86-64
  arranque -> kernel CASM (Ring 0)
                memoria / excepciones / capacidades / puerta
                                      |
                             ABI comprobado y versionado
                                      |
                     runtime Rust -> servicios -> apps (Ring 3)
```

## Las fronteras

CASM es un compilador del anfitrion y un lenguaje del destino. El compilador
puede usar herramientas Windows/Linux; eso no concede servicios de esos SO
al programa que emite. Sus perfiles metal64 y Native tienen contratos distintos.

El kernel concede y comprueba. Politicas de escritorio, formatos de aplicaciones
y compatibilidad viven arriba. El ABI de BMO-X aporta lecciones y una referencia;
no se declara compatible BMO-X2 hasta definir y probar cada contrato necesario.

Dispositivos con firmware y DMA constituyen una frontera propia. La GPU no es
un requisito del primer arranque: antes hay que demostrar aislamiento de CPU,
memoria y entrada/salida del proceso. Un programa Rust no recibe acceso al
hardware por el mero hecho de estar escrito en Rust.

## Que representa un nodo

Una responsabilidad con una ruta real, estado y prueba de aceptacion. Sus
dependencias pueden ser de codigo actual, generacion, verificacion o plan.
El catalogo las etiqueta; una relacion planificada no afirma una llamada actual.
Los archivos existentes siguen siendo los nodos de implementacion que SUPER
GRAFO analiza. Las futuras piezas del kernel contienen solo su contrato inicial.
La excepcion inicial es `kernel/boot/entry.casm`, una fuente propia pequena:
emision y verificacion HOST, con los servicios del cargador metal64. Aun no
inicializa los subsistemas ni acredita un arranque; ver [FIRST-BOOT](FIRST-BOOT.md).

El guardado automatico de SUPER GRAFO organiza crates de Cargo; CASM no es un
workspace Rust. La orden `mapa` llama a ese guardado real y despues aplica
nuestro orden explicito de nodos al formato de posiciones soportado por SG.
Las aristas de plan se conservan en `nodes.json` y `CATALOG.md`; SG obtiene
las aristas de codigo de su analizador, no las inventa a partir del plan.
