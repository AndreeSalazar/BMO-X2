# Fuente de CABINA

`cabina_font.bin` deriva de `platform/shared/bmo-letra` de BMO-X,
commit `6076bdefefc67877419ca53633c6e40cb45fc92d`.
Copyright 2026 Eddi Andree Salazar Matos. Apache-2.0.

El atlas guarda 36 glifos ASCII de CABINA, en el orden
de `font_atlas.rs`. Cada glifo ocupa un byte de avance y 12 filas
de tres bytes, con dos bits de cobertura por pixel. El generador
usa la fuente proporcional del padre, a 11 pixeles y peso medio.
El cliente Rust dibuja tramos del mismo color en Ring 3.

Para regenerarlo desde la raiz, con BMO-X en la carpeta vecina:

```powershell
New-Item -ItemType Directory -Force build/desktop | Out-Null
rustc --edition=2021 --crate-name bmo_letra --crate-type rlib -O ../BMO/platform/shared/bmo-letra/src/lib.rs -o build/desktop/libbmo_letra.rlib
rustc --edition=2024 -O --extern bmo_letra=build/desktop/libbmo_letra.rlib tools/desktop/font_atlas.rs -o build/desktop/font-atlas.exe
cmd.exe /d /c "build\desktop\font-atlas.exe > tools\desktop\cabina_font.bin"
```

El build normal usa el atlas ya generado y puede ejecutarse
sin el checkout del padre.
