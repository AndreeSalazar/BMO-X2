[CmdletBinding()]
param(
    [ValidateSet('comprobar','compilar')][string]$Accion,
    [string]$Python,
    [string]$Compiler,
    [string]$Source
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
if (-not $Compiler) { $Compiler = Join-Path $env:ProgramFiles 'LLVM/bin/clang.exe' }
if (-not (Test-Path -LiteralPath $Compiler -PathType Leaf)) { throw 'Falta Clang. Indicar -Compiler <ruta>.' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Falta Python. Usar bmo-x2.ps1.' }
$outputDir = Join-Path $projectRoot 'build/CASM/host'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$temporaryExe = Join-Path $outputDir 'casmc.build.exe'
$compilerExe = Join-Path $outputDir 'casmc.exe'
$sources = @('main.c','frontend.c','emitter.c') | ForEach-Object { Join-Path $projectRoot "CASM/src/$_" }
$flags = @('-std=c11','-D_CRT_SECURE_NO_WARNINGS','-Wall','-Wextra','-Werror','-pedantic','-O2')
& $Compiler @flags @sources -o $temporaryExe
if ($LASTEXITCODE -ne 0) { throw 'Fallo la semilla C de CASM. No se ejecuta el binario anterior.' }
Move-Item -LiteralPath $temporaryExe -Destination $compilerExe -Force
$version = (& $Compiler --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'No se pudo identificar Clang.' }
$hashes = @($sources + (Join-Path $projectRoot 'CASM/src/casm.h')) | ForEach-Object {
    [ordered]@{ruta=[IO.Path]::GetRelativePath($projectRoot,$_).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_).Hash.ToLowerInvariant()}
}
$toolchain = [ordered]@{schema=1;host='Windows';target='x86-64 metal64 0.2';compiler=$version;flags=$flags;sources=$hashes;executable_sha256=(Get-FileHash -LiteralPath $compilerExe).Hash.ToLowerInvariant()}
$toolchain | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputDir 'toolchain.json') -Encoding utf8
$version | Set-Content -LiteralPath (Join-Path $outputDir 'toolchain.txt') -Encoding utf8
if ($Accion -eq 'comprobar') {
    & $Python -B (Join-Path $projectRoot 'CASM/test.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el banco CASM.' }
    $report = Get-Content -LiteralPath (Join-Path $projectRoot 'build/CASM/test-results.json') -Raw | ConvertFrom-Json
    Write-Output "CASM HOST: $($report.Passed)/$($report.Total) aprobados; $(@($report.Skipped).Count) omitidos. No acredita QEMU ni metal."
    return
}
if (-not $Source) { $Source = Join-Path $projectRoot 'CASM/examples/hello.casm' }
$sourceFile = Get-Item -LiteralPath $Source
if (-not ($sourceFile -is [IO.FileInfo]) -or ($sourceFile.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'La fuente debe ser un archivo regular.'
}
$run = Join-Path $projectRoot ('build/CASM/run-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $run | Out-Null
$frozen = Join-Path $run 'source.casm'
$hex = Join-Path $run 'program.hex'
$ir = Join-Path $run 'program.ir.json'
$log = Join-Path $run 'registro.txt'
Copy-Item -LiteralPath $sourceFile.FullName -Destination $frozen
$sourceFile.FullName | Set-Content -LiteralPath (Join-Path $run 'origen.txt') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $outputDir 'toolchain.txt') -Destination (Join-Path $run 'toolchain.txt')
Copy-Item -LiteralPath (Join-Path $outputDir 'toolchain.json') -Destination (Join-Path $run 'toolchain.json')
& $compilerExe $frozen $hex $ir 2>&1 | Tee-Object -FilePath $log
if ($LASTEXITCODE -ne 0) { throw "Fuente rechazada. No se publico INICIO.X86. Run: $run" }
& $Python -B (Join-Path $projectRoot 'CASM/verify.py') $frozen $hex $ir --packet (Join-Path $run 'INICIO.X86') --report (Join-Path $run 'verified.json') 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { throw "Emision rechazada. Run: $run" }
Write-Output "HOST: HEX, IR y paquete verificados en $run"
