[CmdletBinding()]
param(
    [string]$DoomSource,
    [string]$Gcc,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin')
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
if (-not $DoomSource) {
    $DoomSource = Join-Path (Split-Path $root) 'BMO/toolchain/lang/c/expansion/doom/fuentes/doomgeneric/doomgeneric'
}
if (-not $Gcc) { $Gcc = Join-Path $root 'build/tools/gcc-15.2.0/bin/x86_64-elf-gcc.exe' }
$DoomSource = (Resolve-Path -LiteralPath $DoomSource).Path
$Gcc = (Resolve-Path -LiteralPath $Gcc).Path
$out = (New-Item -ItemType Directory -Force (Join-Path $root 'build/doom-engine')).FullName
$headers = Join-Path $PSScriptRoot 'doom/engine_include'
$shims = Join-Path $PSScriptRoot 'doom/freestanding'
$manifest = Get-Content -LiteralPath (Join-Path $DoomSource 'Makefile') | Where-Object { $_ -match '^SRC_DOOM\s*=' }
$units = @($manifest -split '\s+' | Where-Object { $_ -match '^[a-z0-9_]+\.o$' -and $_ -ne 'doomgeneric_xlib.o' })
if ($units.Count -eq 0) { throw 'No se encontro la lista de objetos DoomGeneric.' }
$flags = @('-m64','-Os','-ffreestanding','-fno-pic','-fno-pie','-fno-stack-protector',
           '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Werror=implicit-function-declaration',
           '-DNORMALUNIX', "-I$headers", "-I$shims")
$objects = foreach ($unit in $units) {
    $object = Join-Path $out $unit
    $source = Join-Path $DoomSource ([IO.Path]::ChangeExtension($unit, 'c'))
    & $Gcc @flags -c $source -o $object
    if ($LASTEXITCODE -ne 0) { throw "Fallo GCC en $unit." }
    $object
}
$wadAdapter = Join-Path $out 'wad_stdio.o'
& $Gcc @flags -c (Join-Path $PSScriptRoot 'doom/wad_stdio.c') -o $wadAdapter
if ($LASTEXITCODE -ne 0) { throw 'Fallo GCC en el adaptador de archivo WAD.' }
$objects += $wadAdapter
$engine = Join-Path $out 'doom-engine.o'
& (Join-Path $Llvm 'ld.lld.exe') -r @objects -o $engine
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace relocatable del motor.' }
$pending = & (Join-Path $Llvm 'llvm-nm.exe') --undefined-only $engine
if ($LASTEXITCODE -ne 0) { throw 'Fallo la lectura de simbolos del motor.' }
$pending | Set-Content -LiteralPath (Join-Path $out 'runtime-imports.txt') -Encoding ascii
& (Join-Path $Llvm 'llvm-size.exe') $engine
if ($LASTEXITCODE -ne 0) { throw 'Fallo la medicion del motor.' }
Write-Output "Motor ELF64 relocatable: $($units.Count) unidades. Dependencias: $($pending.Count)."
Write-Output "Inventario: $(Join-Path $out 'runtime-imports.txt')"
