# Herencia de Ring 3 de BMO-X

Estado en BMO-X2: DISENO. Inventario de BMO-X en
`6076bdefefc67877419ca53633c6e40cb45fc92d`.
La transferencia comienza despues del cierre de la base Ring 0.
Las pruebas del cierre usan programas minimos con stubs de prueba.
[Plan Ring 0](../docs/RING0-PLAN.md).
[Inventario de crates y dependencias declaradas](RING3-CRATES.md).

El orden inicial es adaptar `bmo-userland` y `bmo-rt` al ABI de
BMO-X2, revisar bibliotecas segun dependencias transitivas y validar
Director e input con sus capacidades de servicio. El inventario separa
los productores de toolchain de la carga de usuario. Su columna de
ABI directo orienta la revision antes de compilar cada crate.

| Orden | Origen en BMO-X | Que debe probar BMO-X2 |
|---|---|---|
| 1. Runtime | `Ultra_userspace/userland`, `platform/abi`, `toolchain/lang/base/bmo-rt` | Arranque, pila, finalizacion y wrappers para INVOKE y WAIT en SBEF. Revisar dependencias reales de cada crate. |
| 2. Bibliotecas | `platform/shared`, incluido dibujo, puerta de red, pintura y letra | Clasificar codigo puro y dependencias de ABI. Enlazar y probar cada biblioteca con permisos acotados. |
| 3. Servicios | `Ultra_userspace/services`, incluido Director e input, y `platform/services` | Declarar operaciones, canales, bloques y recursos de dispositivos. Arrancar y recuperar cada servicio sin conceder autoridad implicita. |
| 4. Aplicaciones | `Ultra_userspace/apps` | Reempaquetar en SBEF y reproducir las funciones de cada app con las capacidades de su servicio. Avanzar desde una app minima hasta escritorio y compatibilidad. |
| 5. Medidas y herramientas | `Ultra_userspace/medida` y productores `toolchain/tools` | Distinguir herramientas HOST de programas de usuario. Registrar tamanos, latencia y limites de memoria por carga. |

Para cada componente se registra origen y revision, dependencias,
operaciones del ABI, permisos, formato de entrada, cambios y evidencia.
Los ejecutables BEF2 del padre requieren reempaquetado o una decision de
compatibilidad probada antes de ejecutarse en BMO-X2. Una pieza que pide
un mecanismo aun pendiente queda inventariada con su bloqueo.

El emisor `toolchain/lang/cobol/emisor-x86_64` es una referencia HOST.
Su primer caso de transferencia sera un programa COBOL pequeno,
enlazado con el runtime y empaquetado como SBEF. El crate Rust de
usuario y el programa COBOL deben obtener el mismo resultado de una
operacion del ABI en Ring 3.
