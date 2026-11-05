# Herencia de BMO-X y procedencia de CASM

CASM se copio de `Linux Reconstruido/CASM`, del mismo autor, en el commit
`5a751b1cf493780003ff2714a83e738f2981c1dd`. Su ultimo cambio CASM era
`3a6e796`: modulos freestanding y pruebas adversas.

`casm-origin.json` conserva los 38 archivos importados y el SHA-256 de cada
original. `COPYING-CASM` conserva la licencia del origen. No se han importado
firmware NVIDIA, corpus privados, informes de discos ni ejecutables ajenos.
`.gitattributes` conserva los bytes del snapshot CASM para que sus huellas
sigan siendo comprobables despues de clonar, incluidos sus finales de linea.

Adaptacion local inicial: `CASM/test.py` reconoce Windows, utiliza el ejecutable
`.exe` y registra como omitido el unico caso que exige RLIMIT_DATA. Las demas
pruebas y el emisor/verificador conservan su comportamiento. Las herramientas
PowerShell de este proyecto son nuevas y se identifican como tales.

Maduracion del 05-11: `casm-changes.json` registra las divergencias activas:
modelo compacto, reparto del frontend y manifest de fuentes del bootstrap,
ademas de aquella adaptacion del banco. El registro de SHA-256 de los originales
se conserva; no se reescribe para ocultar los cambios. Los nuevos modulos son
trabajo de BMO-X2 y conservan la frontera de licencia de esta base CASM.

Los enlaces relativos de los documentos heredados pueden referirse a evidencia
que sigue en ULTRA. No se interpreta esa evidencia como una prueba de BMO-X2.

## Lo que se hereda de BMO-X

| Leccion | Aplicacion aqui |
|---|---|
| Declarar, conceder, comprobar | Puerta explicita entre CASM y Rust, con capacidades. |
| Preguntar hechos, fijar contratos | Descubrir hardware; versionar formatos y numeros de ABI. |
| Jueces puros fuera del acceso al aparato | Comprobar aritmetica/layout/admision en host; efectos privilegiados en QEMU y metal. |
| Un verde requiere evidencia | No sumar resultados de distintos builds como una prueba actual. |
| Medida con origen y coste | Distinguir instrucciones, ciclos, tiempo y consumo; medir el instrumento. |
| Una responsabilidad por nodo | Separar por pregunta, contratos y pruebas, conservando los motivos. |
| DMA no equivale a privilegio de CPU | Mantener firmware/aparatos como una frontera independiente. |
| Un intento bueno no prueba fiabilidad | Conservar casos negativos y no reabrir ensayos sin hipotesis refutable. |
| Un comentario tambien envejece | Estado vigente separado de los documentos historicos importados. |

Referencias locales: `BMO/FUERO/`, `BMO/VALKYRIE-ABI/`, `BMO/PERFIL/`,
`BMO/NEUTRO/`, `BMO/BITACORA.md` y `BMO/docs/plan/EL_FOCO.md`.
