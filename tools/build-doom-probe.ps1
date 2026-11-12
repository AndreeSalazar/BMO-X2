[CmdletBinding()]
param(
    [string]$DoomSource,
    [string]$Gcc,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
if (-not $DoomSource) {
    $DoomSource = Join-Path (Split-Path $root) 'BMO/toolchain/lang/c/expansion/doom/fuentes/doomgeneric/doomgeneric'
}
$DoomSource = (Resolve-Path -LiteralPath $DoomSource).Path
if (-not $Python) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($command) { $command.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
$source = Join-Path $DoomSource 'm_fixed.c'
$sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if ($sourceHash -ne '8A5C16CDDF5AC8CB97BA5A3C14ED7F4762DC5A7C423BE49DADD9C7210BF745F4') {
    throw 'm_fixed.c difiere de la fuente DoomGeneric fijada.'
}
$out = (New-Item -ItemType Directory -Force (Join-Path $root 'build/doom-probe')).FullName
$probe = Join-Path $PSScriptRoot 'doom/fixed_probe.c'
$runtime = Join-Path $PSScriptRoot 'doom/fixed_runtime.c'
$headers = Join-Path $PSScriptRoot 'doom/freestanding'
$clang = Join-Path $Llvm 'clang.exe'
$linker = Join-Path $Llvm 'ld.lld.exe'
$readobj = Join-Path $Llvm 'llvm-readobj.exe'

# Use the same input source and assertions for the native executable.
$exe = Join-Path $out 'doom-fixed-host.exe'
& $clang --target=x86_64-pc-windows-msvc -O2 -DBMO_HOST "-I$DoomSource" $source $probe -o $exe
if ($LASTEXITCODE -ne 0) { throw 'Fallo el build HOST de DOOM.' }
& $exe
if ($LASTEXITCODE -ne 0) { throw 'Fallo la aritmetica FixedMul/FixedDiv de DOOM.' }
Write-Output 'HOST: cuatro comprobaciones de FixedMul/FixedDiv aprobadas.'

$cc = if ($Gcc) { $Gcc } else { $clang }
[string[]]$target = if ($Gcc) { @('-m64') } else { @('--target=x86_64-unknown-none-elf') }
$flags = @('-O2','-ffreestanding','-fno-pic','-fno-pie','-fno-stack-protector',
           '-fno-unwind-tables','-fno-asynchronous-unwind-tables',"-I$headers","-I$DoomSource")
$objects = @()
foreach ($unit in @($source, $probe, $runtime, (Join-Path $root 'userspace/runtime/abi/portal.S'))) {
    $obj = Join-Path $out ([IO.Path]::GetFileNameWithoutExtension($unit) + '.o')
    & $cc @target @flags -c $unit -o $obj
    if ($LASTEXITCODE -ne 0) { throw "Fallo el objeto ELF64 de $unit. Para -Gcc usa un GCC con destino x86-64 ELF." }
    $objects += $obj
}
$elf = Join-Path $out 'doom-fixed.elf'
$sbef = Join-Path $out 'doom-fixed.sbef'
$linkScript = Join-Path $root 'userspace/sbef.ld'
& $linker -static -T $linkScript @objects -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace ELF64 de DOOM.' }
$segments = & $readobj --program-headers $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo la lectura de segmentos ELF64.' }
$segments | Set-Content -LiteralPath (Join-Path $out 'elf-segments.txt') -Encoding ascii
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST de SBEF.' }
Write-Output "SBEF: $sbef"
