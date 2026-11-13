[CmdletBinding()]
param(
    [string]$DoomSource,
    [string]$Gcc,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [string]$Python,
    [string]$AbiRun,
    [string]$IntroRun,
    [string]$Wad,
    [switch]$Desktop
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
if (-not $DoomSource) {
    $DoomSource = Join-Path (Split-Path $root) 'BMO/toolchain/lang/c/expansion/doom/fuentes/doomgeneric/doomgeneric'
}
if (-not $Gcc) { $Gcc = Join-Path $root 'build/tools/gcc-15.2.0/bin/x86_64-elf-gcc.exe' }
$DoomSource = (Resolve-Path -LiteralPath $DoomSource).Path
$Gcc = (Resolve-Path -LiteralPath $Gcc).Path
$directory = if ($Desktop) { 'build/desktop-doom' } else { 'build/doom-engine' }
$out = (New-Item -ItemType Directory -Force (Join-Path $root $directory)).FullName
$headers = Join-Path $PSScriptRoot 'doom/engine_include'
$shims = Join-Path $PSScriptRoot 'doom/freestanding'
$manifest = Get-Content -LiteralPath (Join-Path $DoomSource 'Makefile') | Where-Object { $_ -match '^SRC_DOOM\s*=' }
$units = @($manifest -split '\s+' | Where-Object { $_ -match '^[a-z0-9_]+\.o$' -and $_ -ne 'doomgeneric_xlib.o' })
if ($units.Count -eq 0) { throw 'No se encontro la lista de objetos DoomGeneric.' }
$flags = @('-m64','-Os','-ffreestanding','-fno-pic','-fno-pie','-fno-stack-protector',
           '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-Werror=implicit-function-declaration',
           '-DNORMALUNIX', '-DDOOMGENERIC_RESX=320', '-DDOOMGENERIC_RESY=200',
           "-I$headers", "-I$shims", "-I$DoomSource")
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
if (-not $Python) {
    $Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
$profileFlags = @()
if ($Desktop) { $profileFlags = @('-DDESKTOP_DOOM') }
$platform = foreach ($unit in @('engine_memory','engine_format','engine_runtime','engine_platform')) {
    $object = Join-Path $out "$unit.o"
    & $Gcc @flags @profileFlags -mstackrealign -c (Join-Path $PSScriptRoot "doom/$unit.c") -o $object
    if ($LASTEXITCODE -ne 0) { throw "Fallo GCC en $unit." }
    $object
}
$elf = Join-Path $out 'doom-engine.elf'
$sbef = Join-Path $out 'doom-engine.sbef'
if ($Desktop) {
    $portal = Join-Path $out 'portal.o'
    & (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -c (Join-Path $root 'userspace/runtime/abi/portal.S') -o $portal
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el stub ABI del escritorio.' }
    $link = @("-Clinker=$(Join-Path $Llvm 'ld.lld.exe')", '-Clinker-flavor=ld',
        "-Clink-arg=-T$(Join-Path $PSScriptRoot 'doom/engine.ld')", "-Clink-arg=$portal", "-Clink-arg=$engine")
    $link += @($platform | ForEach-Object { "-Clink-arg=$_" })
    $rust = @('--edition=2024','--target','x86_64-unknown-none','-D','warnings','-Cpanic=abort',
        '-Copt-level=z','-Clto=fat','-Crelocation-model=static','-Cforce-unwind-tables=no','--cfg','desktop_doom')
    & rustc @rust @link (Join-Path $PSScriptRoot 'desktop/session.rs') -o $elf
} else {
    & (Join-Path $Llvm 'ld.lld.exe') -static -T (Join-Path $PSScriptRoot 'doom/engine.ld') $engine @platform -o $elf
}
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace final del motor.' }
& $Python -B (Join-Path $PSScriptRoot 'sbef.py') pack $elf $sbef --abi 1
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST del motor.' }
if ($AbiRun) {
    if (-not $Wad) { throw '-AbiRun requiere -Wad.' }
    foreach ($unit in @('desktop/session_gate', 'boot/doom_engine_loader')) {
        $name = Split-Path $unit -Leaf
        $object = Join-Path $out "$name.o"
        & (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -DDOOM_WAD -DDOOM_ENGINE @profileFlags -c (Join-Path $PSScriptRoot "$unit.S") -o $object
        if ($LASTEXITCODE -ne 0) { throw "Fallo el ensamblado de $unit." }
        & (Join-Path $Llvm 'llvm-objcopy.exe') -O binary --only-section=.text $object (Join-Path $out "$name.bin")
        if ($LASTEXITCODE -ne 0) { throw "Fallo la extraccion de $unit." }
    }
    $intro = @()
    if ($IntroRun) { $intro = @('--intro', $IntroRun) }
    $profile = if ($Desktop) { '--desktop-doom' } else { '--doom-engine' }
    $fixture = @($profile,'--session-gate',(Join-Path $out 'session_gate.bin'),
                 '--external-loader',(Join-Path $out 'doom_engine_loader.bin'),'--wad',$Wad)
    & $Python -B (Join-Path $PSScriptRoot 'boot/doom_qemu.py') $AbiRun $sbef @intro @fixture
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el arranque del motor en QEMU.' }
}
