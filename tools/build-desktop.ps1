[CmdletBinding()]
param(
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [string]$Python,
    [switch]$Guest,
    [switch]$Session,
    [string]$AbiRun,
    [string]$IntroRun
)
$ErrorActionPreference = 'Stop'
if ($Session) { $Guest = $true }
if ($AbiRun -and -not $Guest) { throw '-AbiRun requiere -Guest.' }
if ($IntroRun -and -not $AbiRun) { throw '-IntroRun requiere -AbiRun.' }
$root = Split-Path $PSScriptRoot
if (-not $Python) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($command) { $command.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
$target = 'x86_64-unknown-none'
$desktop = Join-Path $root 'userspace/services/desktop'
$build = New-Item -ItemType Directory -Force (Join-Path $root 'build/desktop')
$library = Join-Path $build.FullName 'libbmo_x2_desktop.rlib'
$portal = Join-Path $build.FullName 'portal.o'
$elf = Join-Path $build.FullName 'desktop.elf'
$image = Join-Path $build.FullName 'desktop.sbef'
$linker = Join-Path $Llvm 'ld.lld.exe'
$linkScript = Join-Path $root 'userspace/sbef.ld'
$entrySource = Join-Path $desktop 'src/bin/desktop_probe.rs'
$guestFlags = @()
if ($Session) {
    $linkScript = Join-Path $PSScriptRoot 'desktop/guest.ld'
    $elf = Join-Path $build.FullName 'desktop-session.elf'
    $image = Join-Path $build.FullName 'desktop-session.sbef'
    $entrySource = Join-Path $PSScriptRoot 'desktop/session.rs'
}
$fixtureArguments = @()
if ($Session) {
    $gateObject = Join-Path $build.FullName 'session-gate.o'
    $gateBin = Join-Path $build.FullName 'session-gate.bin'
    & (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -c (Join-Path $PSScriptRoot 'desktop/session_gate.S') -o $gateObject
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la puerta de sesion.' }
    & (Join-Path $Llvm 'llvm-objcopy.exe') -O binary --only-section=.text $gateObject $gateBin
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la extraccion de la puerta de sesion.' }
    $fixtureArguments = @('--session-gate', $gateBin)
} elseif ($Guest) {
    $linkScript = Join-Path $PSScriptRoot 'desktop/guest.ld'
    $elf = Join-Path $build.FullName 'desktop-guest.elf'
    $image = Join-Path $build.FullName 'desktop-guest.sbef'
}
$flags = @('--edition=2024', '--target', $target, '-D', 'warnings', '-C', 'panic=abort',
           '-C', 'opt-level=s', '-C', 'relocation-model=static', '-C', 'force-unwind-tables=no')
& rustc @flags --crate-name bmo_x2_desktop --crate-type rlib (Join-Path $desktop 'src/lib.rs') -o $library
if ($LASTEXITCODE -ne 0) { throw 'Fallo el build Rust. Verifica rustup target add x86_64-unknown-none.' }
& (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -c (Join-Path $root 'userspace/runtime/abi/portal.S') -o $portal
if ($LASTEXITCODE -ne 0) { throw 'Fallo el stub ABI.' }
$linkFlags = @('-C', "linker=$linker", '-C', 'linker-flavor=ld', '-C', 'lto=fat',
               '-C', "link-arg=-T$linkScript", '-C', "link-arg=$portal")
if ($Guest -and -not $Session) {
    $complete = Join-Path $build.FullName 'desktop-complete.o'
    $present = Join-Path $build.FullName 'desktop-present.o'
    $presentBin = Join-Path $build.FullName 'desktop-present.bin'
    foreach ($unit in @(@{ Name='guest_complete.S'; Output=$complete }, @{ Name='guest_present.S'; Output=$present })) {
        & (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -c (Join-Path $PSScriptRoot "desktop/$($unit.Name)") -o $unit.Output
        if ($LASTEXITCODE -ne 0) { throw 'Fallo un stub de la sonda grafica.' }
    }
    & (Join-Path $Llvm 'llvm-objcopy.exe') -O binary --only-section=.text $present $presentBin
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la extraccion del presentador.' }
    $guestFlags = @('--cfg','qemu_desktop','-C',"link-arg=$complete")
    $fixtureArguments = @('--desktop-present', $presentBin)
}
& rustc @flags @linkFlags @guestFlags --crate-name desktop_probe --extern "bmo_x2_desktop=$library" $entrySource -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace ELF del escritorio.' }
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $image --abi 1
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST del escritorio.' }
Write-Output "SBEF: $image"
if ($AbiRun) {
    $introArguments = @()
    if ($IntroRun) { $introArguments = @('--intro', $IntroRun) }
    & $Python -B (Join-Path $PSScriptRoot 'boot/doom_qemu.py') $AbiRun $image @fixtureArguments @introArguments
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la sonda grafica en QEMU.' }
}
