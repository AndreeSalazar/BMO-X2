[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$AbiRun,
    [string]$Python,
    [string]$VerranoBsf,
    [string]$BmoRoot
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (-not $Python) { $Python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
$llvm=Join-Path $env:ProgramFiles 'LLVM/bin'
$bank = if ($VerranoBsf) { 'build/verrano-bsf-guest' } else { 'build/rmlui-guest' }
$output=(New-Item -ItemType Directory -Force (Join-Path $root $bank)).FullName
$flags=@('--edition=2024','--target=x86_64-unknown-none','-Cpanic=abort','-Copt-level=z','-Crelocation-model=static','-Cforce-unwind-tables=no')
$gateFlags = @('-DDESKTOP_EXTERNAL')
$loader = 'kernel/loader/external_sbef.S'
$linkScript = Join-Path $PSScriptRoot 'guest.ld'
$mappedLimit = 16384
if ($VerranoBsf) {
    $gateFlags = @('-DDOOM_ENGINE', '-DDESKTOP_DOOM', '-DRMLUI_NATIVE')
    $loader = 'kernel/loader/doom_engine_loader.S'
    $linkScript = Join-Path $PSScriptRoot 'native/guest.ld'
    $mappedLimit = 20480
}
foreach ($unit in @(
    @{Source='userspace/runtime/abi/sysv/portal.S'; Name='portal'; Flags=@()},
    @{Source='kernel/syscalls/session_gate.S';Name='session-gate';Flags=$gateFlags},
    @{Source=$loader;Name='external-loader';Flags=@($gateFlags | Where-Object { $_ -eq '-DRMLUI_NATIVE' })}
)) {
    $obj=Join-Path $output ($unit.Name+'.o')
    & (Join-Path $llvm 'clang.exe') --target=x86_64-unknown-none-elf @($unit.Flags) -c (Join-Path $root $unit.Source) -o $obj
    if ($LASTEXITCODE -ne 0) {throw 'Fallo ensamblado de fixture.'}
    & (Join-Path $llvm 'llvm-objcopy.exe') -O binary --only-section=.text $obj (Join-Path $output ($unit.Name+'.bin'))
    if ($LASTEXITCODE -ne 0) {throw 'Fallo extraccion de fixture.'}
}
$linkFlags = @('-Clto=fat', '-Clinker-flavor=ld', "-Clinker=$llvm/ld.lld.exe",
               "-Clink-arg=-T$linkScript", "-Clink-arg=$output/portal.o")
function Invoke-GuestProbe($Name, $Source, $Profile, $Expected, [string[]]$Dependencies = @()) {
    $elf = Join-Path $output "$Name.elf"
    $sbef = Join-Path $output "$Name.sbef"
    & rustc @flags @linkFlags @Dependencies $Source -o $elf
    if ($LASTEXITCODE -ne 0) {throw 'Fallo ELF Rust freestanding.'}
    & $Python (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1 --size-report --max-file-bytes 16512 --max-mapped-bytes $mappedLimit
    if ($LASTEXITCODE -ne 0) {throw 'SBEF rechazado; conservar presupuesto.'}
    $gate = Join-Path $output 'session-gate.bin'
    $loader = Join-Path $output 'external-loader.bin'
    & $Python (Join-Path $root 'tools/boot/doom_qemu.py') $AbiRun $sbef --session-gate $gate --external-loader $loader $Profile $Expected
    if ($LASTEXITCODE -ne 0) {throw 'Fallo prueba real CPL3.'}
}

if (-not $VerranoBsf) {
    $hostScene = Join-Path $output 'host-scene.exe'
    $expected = Join-Path $output 'expected.bin'
    & rustc (Join-Path $PSScriptRoot 'host_scene.rs') --edition=2024 -O -o $hostScene
    if ($LASTEXITCODE -ne 0) {throw 'Fallo referencia Rust HOST.'}
    & $hostScene $expected
    if ($LASTEXITCODE -ne 0) {throw 'Fallo imagen de referencia.'}
    Invoke-GuestProbe 'raster' (Join-Path $PSScriptRoot 'guest.rs') '--rmlui-renderer' $expected
    return
}

$valid = Get-Item -LiteralPath $VerranoBsf
if ($valid.Length -lt 64 -or $valid.Length -gt 4096) { throw 'BSF fuera del presupuesto de la sonda.' }
if (-not $BmoRoot) { $BmoRoot = Join-Path (Split-Path $root) 'BMO' }
$bsfFlags = $flags[1..($flags.Length - 1)]
$bsf = & (Join-Path $root 'tools/host/gpu/build-bsf.ps1') -BmoRoot $BmoRoot -Output $output -RustFlags $bsfFlags
$verrano = Join-Path $output 'libbmo_x2_verrano.rlib'
$verranoRoot = Join-Path $root 'userspace/services/graphics/verrano'
& rustc @flags --crate-type=rlib --crate-name bmo_x2_verrano (Join-Path $verranoRoot 'lib.rs') -o $verrano
if ($LASTEXITCODE) { throw 'Fallo la biblioteca VERRANO.' }
$dependencies = @('-L', "dependency=$output", '--extern', "bmo_bsf=$bsf", '--extern', "bmo_x2_verrano=$verrano")
$corrupt = Join-Path $output 'corrupt.bsf'
$changed = [IO.File]::ReadAllBytes($valid.FullName)
$changed[-1] = $changed[-1] -bxor 1
[IO.File]::WriteAllBytes($corrupt, $changed)
$oldBsf = $env:VERRANO_BSF
try {
    foreach ($case in @(
        @{Name='bsf-valid'; Package=$valid.FullName; Left=0x00ff5c82; Right=0x005ad8ff},
        @{Name='bsf-corrupt'; Package=$corrupt; Left=0x00ba382e; Right=0x00ba382e}
    )) {
        $expected = Join-Path $output ($case.Name + '.bin')
        $pixels = [byte[]]::new(16 * 16 * 4)
        for ($index = 0; $index -lt 256; $index++) {
            $color = if ($index % 16 -lt 8) { $case.Left } else { $case.Right }
            [BitConverter]::GetBytes([uint32]$color).CopyTo($pixels, $index * 4)
        }
        [IO.File]::WriteAllBytes($expected, $pixels)
        $env:VERRANO_BSF = $case.Package
        Invoke-GuestProbe $case.Name (Join-Path $verranoRoot 'guest.rs') '--verrano-bsf' $expected $dependencies
    }
} finally {
    $env:VERRANO_BSF = $oldBsf
}
