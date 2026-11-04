# Herramientas del anfitrion

`project.py` valida nodos, genera notas/catalogo y aplica el orden de SG.
`host.ps1` construye la semilla C de metal64 con Clang, corre su banco y
publica un run con HEX/IR comprobados. No construye todavia un kernel.
`super-grafo.ps1` construye SG desde sus fuentes locales, con dependencias ya
disponibles, y deja el ejecutable dentro de `build/` de BMO-X2.

Entrar por `../bmo-x2.ps1`. Python y Clang se resuelven como herramientas
explicitas; no se descarga ni instala nada. Los resultados van a `build/`.
