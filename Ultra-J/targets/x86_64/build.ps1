[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$View,
    [Parameter(Mandatory)][string]$Python,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin')
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$viewPath = Get-Item -LiteralPath $View
if ($viewPath.PSIsContainer) { throw 'La vista UJVI debe ser un archivo.' }
$output = (New-Item -ItemType Directory -Force (Join-Path $root 'build/ultra-j/x86_64')).FullName
$object = Join-Path $output 'view.o'
$elf = Join-Path $output 'view.elf'
$sbef = Join-Path $output 'view.sbef'

# LLVM reads the exact view path through its preprocessor before assembling .incbin.
$viewDefine = '-DUJ_VIEW_FILE=\"' + ($viewPath.FullName -replace '\\', '/') + '\"'
& (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf $viewDefine -c (Join-Path $PSScriptRoot 'guest_view.S') -o $object
if ($LASTEXITCODE -ne 0) { throw 'Fallo el ensamblado del presentador x86-64.' }
& (Join-Path $Llvm 'ld.lld.exe') -T (Join-Path $root 'tools/desktop/external.ld') $object -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace x86-64 de la vista.' }
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1 --size-report | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST de la vista SBEF.' }
$sbef
