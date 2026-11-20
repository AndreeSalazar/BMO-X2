[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$View,
    [Parameter(Mandatory)][string]$Python,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [switch]$Benchmark
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$viewPath = Get-Item -LiteralPath $View
if ($viewPath.PSIsContainer -or $viewPath.Length -gt 3576) { throw 'UJVI debe caber en 3576 bytes.' }
$output = (New-Item -ItemType Directory -Force (Join-Path $root 'build/ultra-j/x86_64')).FullName
$name = if ($Benchmark) { 'view-benchmark' } else { 'view' }
$object = Join-Path $output "$name.o"
$elf = Join-Path $output "$name.elf"
$sbef = Join-Path $output "$name.sbef"
$flags = @()
$objects = @($object)
if ($Benchmark) {
    $rustObject = Join-Path $output 'benchmark.o'
    & rustc --edition=2021 --target=x86_64-unknown-none --crate-type lib --emit obj -C panic=abort -C opt-level=2 -C relocation-model=static -C code-model=small -C no-redzone=yes -C force-unwind-tables=no (Join-Path $PSScriptRoot 'benchmark.rs') -o $rustObject
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del banco Rust.' }
    $objects += $rustObject
    $flags += '-DUJ_BENCHMARK'
}

# Clang must receive the quotes for .incbin in both PowerShell argument modes.
$viewQuote = if ($PSNativeCommandArgumentPassing -in @('Standard', 'Windows')) { '"' } else { '\"' }
$viewDefine = '-DUJ_VIEW_FILE=' + $viewQuote + ($viewPath.FullName -replace '\\', '/') + $viewQuote
& (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf $viewDefine @flags -c (Join-Path $PSScriptRoot 'guest_view.S') -o $object
if ($LASTEXITCODE -ne 0) { throw 'Fallo el ensamblado del presentador x86-64.' }
& (Join-Path $Llvm 'ld.lld.exe') -T (Join-Path $root 'tools/desktop/external.ld') @objects -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace x86-64 de la vista.' }
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1 --size-report | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST de la vista SBEF.' }
$sbef
