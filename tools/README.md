# Herramientas del anfitrion

El lanzador y `host.ps1` admiten Windows PowerShell 5.1 y PowerShell 7.
`paths.ps1` conserva las rutas de fuentes relativas sin depender de una API
de .NET Core; `tests/paths.ps1` comprueba nombres con espacios y rechazos de
rutas externas. El formato de HEX y los bytes del programa no cambian.

`project.py` valida nodos, genera notas/catalogo y aplica el orden de SG.
`host.ps1` construye la semilla C de metal64 con Clang, corre su banco y
publica un run con HEX/IR comprobados. No construye todavia un kernel.
`super-grafo.ps1` construye SG desde sus fuentes locales, con dependencias ya
disponibles, y deja el ejecutable dentro de `build/` de BMO-X2.

`-Accion comprobar` incluye invariantes del almacenamiento C. `-Accion medir`
reconstruye la base d2575a8 y compara 333 casos con el compilador actual. Antes
de medir comprueba que las fuentes y el binario coinciden con su registro de
construccion, y que la base usa el mismo Clang y flags.

Entrar por `../bmo-x2.ps1`. Python y Clang se resuelven como herramientas
explicitas; no se descarga ni instala nada. Los resultados van a `build/`.
