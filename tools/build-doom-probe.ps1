[CmdletBinding()]
param(
    [string]$DoomSource,
    [string]$Gcc,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [string]$Python,
    [string]$AbiRun,
    [string]$IntroRun,
    [switch]$External
)
$ErrorActionPreference = 'Stop'
if ($IntroRun -and -not $AbiRun) { throw '-IntroRun requiere -AbiRun.' }
if ($External -and (-not $Gcc -or -not $AbiRun)) { throw '-External requiere -Gcc y -AbiRun.' }
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
if ($External) { $flags += '-DBMO_EXTERNAL' }
foreach ($unit in @($source, $probe, $runtime, (Join-Path $PSScriptRoot 'doom/complete.S'), (Join-Path $root 'userspace/runtime/abi/portal.S'))) {
    $obj = Join-Path $out ([IO.Path]::GetFileNameWithoutExtension($unit) + '.o')
    & $cc @target @flags -c $unit -o $obj
    if ($LASTEXITCODE -ne 0) { throw "Fallo el objeto ELF64 de $unit. Para -Gcc usa un GCC con destino x86-64 ELF." }
    $objects += $obj
}
$elf = Join-Path $out 'doom-fixed.elf'
$sbef = Join-Path $out 'doom-fixed.sbef'
$linkScript = Join-Path $root 'userspace/sbef.ld'
if ($External) {
    $linkScript = Join-Path $PSScriptRoot 'desktop/external.ld'
    $elf = Join-Path $out 'doom-external.elf'
    $sbef = Join-Path $out 'doom-external.sbef'
}
& $linker -static -T $linkScript @objects -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace ELF64 de DOOM.' }
$segments = & $readobj --program-headers $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo la lectura de segmentos ELF64.' }
$segments | Set-Content -LiteralPath (Join-Path $out 'elf-segments.txt') -Encoding ascii
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST de SBEF.' }
Write-Output "SBEF: $sbef"
if ($AbiRun) {
    $introArguments = @()
    if ($IntroRun) { $introArguments = @('--intro', $IntroRun) }
    $fixture = @()
    if ($External) {
        $objcopy = Join-Path $Llvm 'llvm-objcopy.exe'
        foreach ($unit in @('desktop/session_gate', 'boot/external_sbef')) {
            $name = Split-Path $unit -Leaf
            & $clang --target=x86_64-unknown-none-elf -c (Join-Path $PSScriptRoot "$unit.S") -o (Join-Path $out "$name.o")
            if ($LASTEXITCODE -ne 0) { throw "Fallo el ensamblado de $unit." }
            & $objcopy -O binary --only-section=.text (Join-Path $out "$name.o") (Join-Path $out "$name.bin")
            if ($LASTEXITCODE -ne 0) { throw "Fallo la extraccion de $unit." }
        }
        $fixture = @('--doom-external','--session-gate',(Join-Path $out 'session_gate.bin'),
                     '--external-loader',(Join-Path $out 'external_sbef.bin'))
    }
    & $Python -B (Join-Path $PSScriptRoot 'boot/doom_qemu.py') $AbiRun $sbef @introArguments @fixture
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la ejecucion de la sonda DOOM en QEMU.' }
}
