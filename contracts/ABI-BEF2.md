# BEF2 y el ABI entre Ring 3 y Ring 0

Referencia de herencia. El diseno del encabezado propio de BMO-X2 y su
orden de implementacion viven en [SBEF](SBEF.md).

Estado en BMO-X2: DISENO. La referencia es BMO-X, revision
`6076bdefefc67877419ca53633c6e40cb45fc92d`. Alli, el formato vive en
`platform/abi/bmo-abi/src/bef2/`, su lector de admision en
`platform/abi/bmo-bex-gate/src/lib.rs` y las llamadas en
`platform/abi/bmo-abi/src/syscalls/mod.rs`. Estos archivos son referencia
para escribir la implementacion de Ring 0 en CASM.

| Contrato | Productor | Consumidor | Responsabilidad |
|---|---|---|---|
| Imagen del kernel | CASM y verificador independiente | Cargador de arranque | Entregar bytes x86-64, punto de entrada y contexto inicial. El ensayo actual usa FAGRAW64. |
| BEF2 | Enlazador/empaquetador de Ring 3 | Cargador de procesos en Ring 0 | Declarar regiones, entrada, requisitos de CPU y anexos de un `.bex`. |
| ABI de llamadas | Bibliotecas de Rust, C y C++ | Puerta de servicios en CASM | Transportar operacion, capacidad, argumentos y resultado durante la ejecucion. |

Rust, C y C++ generan codigo maquina x86-64 y datos. El empaquetador pone
esas regiones en un `.bex` y escribe una cabecera BEF2 comun. Las bibliotecas
de cada lenguaje traducen sus llamadas al mismo ABI. Por ejemplo, un buffer
se presenta con direccion y longitud, y un objeto del kernel por su handle.
Las estructuras de argumentos se definen por ancho, alineacion y offsets.
El runtime de cada lenguaje conserva sus objetos y convenciones internas.

## Cabecera BEF2 de BMO-X

La cabecera fija mide 64 bytes. Los enteros se codifican en little endian.

| Offset decimal | Campo de BMO-X | Efecto |
|---:|---|---|
| 0 | `42 45 46 32` (`BEF2`) | Identifica el formato x86-64. |
| 4 | ABI `u8`, banderas `u8`, reservado `u16` | ABI 2 en BMO-X y reserva en cero. |
| 8 | Mascara `xcr0`, `u64` | Estado de CPU requerido por el programa. |
| 16 | Entrada `u32`, cantidad de anexos `u32` | Entrada relativa al codigo y tabla desde el byte 64. |
| 24 | Codigo, offset y longitud `u32` | Paginas de usuario RX. |
| 32 | Constantes, offset y longitud `u32` | Paginas de usuario R+NX. |
| 40 | Datos, offset y longitud `u32` | Paginas de usuario RW+NX. |
| 48 | Longitud de ceros `u32`, total de fichero `u32` | Region RW+NX inicializada a cero y tamano declarado. |
| 56 | Reservado `u64` | Cero. |

Cada anexo mide 16 bytes en el indice. El formato heredado asigna al
cargador relocaciones, firma y requisitos. Los demas anexos pasan controles
de rango y solape y sus contenidos quedan para las herramientas de Ring 3.
La politica de firma y capacidades se valida aparte de la forma del fichero.

## ABI de peticiones

El ABI de BMO-X ofrece `INVOKE` para una operacion sobre una capacidad y
`WAIT` para una espera. Usa registros x86-64 y devuelve estado y valor. Esta
es la referencia para BMO-X2. La primera prueba necesita una sola operacion
con resultado observable y una version de ABI elegida antes de emitir sus
stubs. La puerta toma la identidad del proceso activo, comprueba capacidad,
operacion y argumentos, y acota cada rango de memoria de usuario antes de
copiar. El encabezado BEF2 se consulta al admitir la imagen del proceso.

## Criterio de cierre en BMO-X2

1. Definir el contexto de entrada, el mapa de memoria y una excepcion
   observable en CASM. Asociar fuente, IR, offsets y HEX de cada operacion.
2. Probar la admision de un `.bex` minimo de BMO-X. Comparar su mapa y su
   diagnostico con un lector independiente. Rechazar truncado, ABI ajeno,
   rangos desbordados, solapes y entrada fuera de codigo.
3. Aplicar permisos de paginas y ejecutar el programa en Ring 3 en QEMU.
   Verificar la peticion y la respuesta, una capacidad invalida y un buffer
   fuera de la memoria del proceso.
4. Usar el mismo caso desde Rust, C y C++ y comparar las peticiones y
   respuestas observadas en Ring 0.

SUPER GRAFO muestra los nodos de imagen, BEF2 y ABI con sus estados. El
Taller CASM muestra bytes de una compilacion verificada de la fuente exacta.
La siguiente vista puede asociar cada campo del `.bex` con su offset y con
la regla de admision, usando la salida del verificador como entrada.
