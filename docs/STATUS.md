# Estado de la base BMO-X2 -- 04-11-2026

## Lo hecho aqui

- 38 archivos CASM importados del mismo autor, con commit y SHA-256 de origen.
- 35 nodos de responsabilidad, 49 relaciones tipadas y notas visibles por ruta
  en SUPER GRAFO. Las relaciones de plan no son llamadas de codigo.
- Distribucion inicial compacta por familias, con posiciones de detalle guardadas.
- Herramientas Windows para construir, comprobar, emitir HEX y consultar SG.
- Estructura en ingles: CASM, kernel y userspace; CPU en kernel/arch/x86_64.
- Primera fuente nueva kernel/boot/entry.casm: emision HOST de 48 bytes de
  cuerpo y paquete verificado de 72 bytes; usa servicios del cargador metal64.
- Perfil CASM x86-64: 16 necesidades, con dos heredadas, cinco parciales y
  nueve pendientes; son estados del inventario, no porcentajes de terminacion.
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

Concretar C1 de [CASM-ROADMAP](CASM-ROADMAP.md): lenguaje y perfil de destino del
kernel, tomando funciones/bucles/buffers de la experiencia Native y el contrato
de emision/verificacion de metal64. Despues repartir el frontend con equivalencia
de bytes y ampliar el Taller CASM para sus reglas distribuidas.

Las operaciones privilegiadas, los subsistemas del kernel y el runtime Rust
siguen en DISENO; la sonda de entrada esta compilada en HOST.
No se ha arrancado BMO-X2 en QEMU o en el Ryzen, ni se ha desplegado
a discos. No se aplico el parche incompleto 0.3.
