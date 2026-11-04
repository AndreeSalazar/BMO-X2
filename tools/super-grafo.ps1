# Construye la herramienta desde las fuentes locales, sin modificarlas ni descargar paquetes.
[CmdletBinding()]
param([string]$SourceRoot)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
if (-not $SourceRoot) { $SourceRoot = Join-Path (Split-Path $projectRoot) 'SUPER GRAFO' }
$manifest = Join-Path $SourceRoot 'ultra-carpetas/Cargo.toml'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { throw 'No se encontraron las fuentes locales de SUPER GRAFO.' }
$targetDirectory = Join-Path $projectRoot 'build/tools/super-grafo'
& cargo build --release --offline --locked --manifest-path $manifest --target-dir $targetDirectory --bin ultra-carpetas
if ($LASTEXITCODE -ne 0) { throw 'Fallo la construccion local de SUPER GRAFO.' }
Write-Output "SUPER GRAFO construido en $targetDirectory/release/ultra-carpetas.exe"
