# Herencia concreta para el despertar de BMO-X2

Revision de fuentes locales: 05-11-2026. `transfer.json` registra rutas, commits
observados y SHA-256 de los archivos leidos del arbol de trabajo. No es una
importacion ni una certificacion de ejecucion de BMO-X2.

| Origen | Pieza existente | Aplicacion prevista | Condicion de transferencia |
|---|---|---|---|
| TALK-CPU | Puente_Metal, paquete FAGRAW64 y contexto RDI/R15 | Primer recorrido UEFI -> salida de BootServices -> entrada CASM | Revisar contexto, pila y retorno; reconstruir y repetir pruebas con la entrada BMO-X2. |
| TALK-CPU | Diagnosticos x86-64, IDT/TSS/IST en la ruta ROM | Referencia para excepciones propias | La ruta ROM y el puente UEFI tienen estados de entrada diferentes; no intercambiar sus direcciones. |
| BMO-X | userland/src/sys.rs | Runtime Rust Ring 3 | CASM debe implementar la puerta acordada y su resultado; no basta copiar wrappers. |
| BMO-X | userland/link.ld | Referencia de colocacion de imagen | Elegir formato, mapa virtual, permisos y cargador BMO-X2 antes de reutilizar binarios. |
| BMO-X | userland/Cargo.toml | Dependencias reales del runtime | Auditar bmo-dibujo, bmo-puerta-red, bmo-pinta y bmo-letra por separado; no copiar solo userland. |
| BMO-X | bmo-abi y VALKYRIE-ABI | Numeros y jueces de compatibilidad | Fijar la superficie minima de BMO-X2 y comprobar ambos lados con casos positivos y negativos. |

## El padre entrega experiencia y codigo; el hijo demuestra compatibilidad

El kernel nuevo se escribe en CASM. El Rust del padre se reutiliza en Ring 3
por piezas, con procedencia y contrato. Las herramientas del anfitrion y los
jueces no son codigo privilegiado del kernel por estar escritos en Rust.

La fuente actual de BMO-X declara INVOKE y WAIT; channel_kick usa INVOKE con
una operacion de canal. El antiguo numero 1 figura reservado en bmo-abi.
El README de Ultra_userspace enumera tres llamadas y describe dependencias
antiguas: esta revision toma los archivos fuente como referencia, sin corregir
ni modificar el proyecto padre.

## Despertar por entregas comprobables

1. Repetir en QEMU el contexto del puente con la entrada CASM actual: mensaje,
   retorno, bytes cargados exactos y CPL observado. Sin instalacion en discos.
2. Definir el contexto minimo propio. Sustituir servicios del cargador uno por
   uno con operaciones CASM verificadas; comprobar excepciones antes de ampliar.
3. Elegir imagen, memoria y permisos; establecer la entrada y pila de Ring 3.
4. Ejecutar un programa Rust minimo con una operacion concedida, otra denegada
   y un fallo contenido. Despues transferir servicios mayores del padre.

Independencia del sistema operativo anfitrion no equivale a reemplazar la
inicializacion del firmware de la placa. El puente de TALK-CPU la aprovecha;
la investigacion desde RESET es una ruta separada.

## Menor consumo con una cuenta concreta

Registrar por entrega: bytes de codigo/datos/imagen, memoria reservada y usada,
coste de operacion y comportamiento en reposo. Energia requiere instrumento,
duracion y carga comparables; ni bytes menores ni una parada HLT por si solos
demuestran menos vatios. Comparar siempre la misma funcion y registrar el coste
de la mejora. No hay aun una medida nueva de consumo del kernel BMO-X2.
