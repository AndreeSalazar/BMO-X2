# Vectores binarios ULTRA-J

Los archivos `.hex` son los vectores manuales del [contrato](../../../contracts/ULTRA-J.md).
Para materializar los binarios y probar en HOST desde la raiz, en PowerShell:

```powershell
$ujPython = (Get-Command python -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $ujPython) {
    $ujPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
$ujOutput = New-Item -ItemType Directory -Force .\build\ultra-j
foreach ($ujFile in @('window.ujb', 'graphite.ujt')) {
    $ujWords = (Get-Content ".\userspace\runtime\ultra-j\$ujFile.hex" -Raw).Trim() -split '\s+'
    [byte[]]$ujBytes = foreach ($ujWord in $ujWords) { [Convert]::ToByte($ujWord, 16) }
    [IO.File]::WriteAllBytes((Join-Path $ujOutput.FullName $ujFile), $ujBytes)
}
& $ujPython -B .\tools\ultra_j.py .\build\ultra-j\window.ujb .\build\ultra-j\graphite.ujt
& $ujPython -B .\tools\test_ultra_j.py
```

El primer cierre recupera 64 bytes de tres objetos. La segunda region
usa de nuevo el offset cero y recupera 32 bytes al cerrar. El informe
separa ese pico de 64 bytes de los 256 reservados por la arena.
Cambiar el tema solo altera la tabla de apariencia. La sonda HOST
informa los estilos y el ciclo de memoria. La ventana visible en QEMU
requiere la integracion con DIRECTOR.
