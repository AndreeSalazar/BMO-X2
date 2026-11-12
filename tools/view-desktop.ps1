[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$build = (New-Item -ItemType Directory -Force (Join-Path $root ('build/desktop/preview-' + [guid]::NewGuid().ToString('N')))).FullName
$source = Join-Path $root 'userspace/services/desktop/src/lib.rs'
$library = Join-Path $build 'libbmo_x2_desktop.rlib'
$renderer = Join-Path $build 'renderer.exe'
$flags = @('--edition=2024', '-D', 'warnings', '-C', 'opt-level=2')
& rustc @flags --crate-name bmo_x2_desktop --crate-type rlib $source -o $library
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del compositor Rust.' }
& rustc @flags --extern "bmo_x2_desktop=$library" (Join-Path $PSScriptRoot 'desktop/preview.rs') -o $renderer
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del presentador HOST.' }

$ready = Join-Path $build 'ready.txt'
$stdout = Join-Path $build 'stdout.log'
$stderr = Join-Path $build 'stderr.log'
$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-File',
               ('"{0}"' -f (Join-Path $PSScriptRoot 'desktop/view.ps1')),
               ('"{0}"' -f $renderer), ('"{0}"' -f $ready))
$shell = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$window = Start-Process -FilePath $shell -ArgumentList $arguments -WindowStyle Normal -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
for ($attempt = 0; $attempt -lt 50; $attempt++) {
    $window.Refresh()
    if ((Test-Path -LiteralPath $ready) -and $window.MainWindowTitle -like '*Escritorio Rust*') {
        Write-Output "Vista previa HOST abierta (PID $($window.Id)). Captura: $(Join-Path $build 'preview.png')"
        return
    }
    if ($window.WaitForExit(100)) { break }
}
throw "La ventana HOST no confirmo su inicio. $(Get-Content -LiteralPath $stderr -Raw)"
