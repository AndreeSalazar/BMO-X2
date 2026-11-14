# ULTRA-J

`compiler.py` compila el [ejemplo de escritura Java](examples/WindowDemo.uj)
a `.ujb`. `runtime.py` verifica y ejecuta en HOST. `examples/` guarda
el tema y el vector manual que define los bytes esperados.
El [contrato](FORMAT.md) especifica las instrucciones y el alcance.

Desde la raiz de BMO-X2, en PowerShell:

```powershell
$ujPython = (Get-Command python -CommandType Application -ErrorAction SilentlyContinue).Source
if (-not $ujPython) {
    $ujPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
$ujOutput = New-Item -ItemType Directory -Force .\build\ultra-j
$ujWords = (Get-Content .\Ultra-J\examples\graphite.ujt.hex -Raw).Trim() -split '\s+'
[byte[]]$ujBytes = foreach ($ujWord in $ujWords) { [Convert]::ToByte($ujWord, 16) }
[IO.File]::WriteAllBytes((Join-Path $ujOutput.FullName 'graphite.ujt'), $ujBytes)
& $ujPython -B .\Ultra-J\compiler.py .\Ultra-J\examples\WindowDemo.uj .\build\ultra-j\window.ujb
& $ujPython -B .\Ultra-J\runtime.py .\build\ultra-j\window.ujb .\build\ultra-j\graphite.ujt
& $ujPython -B .\Ultra-J\test_ultra_j.py
```

El primer cierre recupera 64 bytes de tres objetos. La segunda region
usa de nuevo el offset cero y recupera 32 bytes al cerrar. El informe
separa ese pico de 64 bytes de los 256 reservados por la arena.
Cambiar el tema solo altera la tabla de apariencia. La sonda HOST
informa los estilos y el ciclo de memoria. La ventana visible en QEMU
requiere la integracion con DIRECTOR.

Agrega `--watch` al comando de `compiler.py` para compilar al guardar.
Consulta el fuente cada 250 ms. Publica el binario verificado mediante un
reemplazo atomico y conserva el ultimo binario valido si hay un error.
Deten el proceso con Ctrl+C.
