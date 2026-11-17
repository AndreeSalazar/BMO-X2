[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$AbiRun, [string]$Python)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (-not $Python) { $Python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
$llvm=Join-Path $env:ProgramFiles 'LLVM/bin'
$output=(New-Item -ItemType Directory -Force (Join-Path $root 'build/rmlui-guest')).FullName
$flags=@('--edition=2024','--target=x86_64-unknown-none','-Cpanic=abort','-Copt-level=z','-Crelocation-model=static','-Cforce-unwind-tables=no')
& rustc (Join-Path $PSScriptRoot 'host_scene.rs') --edition=2024 -O -o (Join-Path $output 'host-scene.exe')
if ($LASTEXITCODE -ne 0) {throw 'Fallo referencia Rust HOST.'}
& (Join-Path $output 'host-scene.exe') (Join-Path $output 'expected.bin')
if ($LASTEXITCODE -ne 0) {throw 'Fallo imagen de referencia.'}
foreach ($unit in @(
    @{Source='userspace/runtime/abi/sysv/portal.S'; Name='portal'; Flags=@()},
    @{Source='kernel/syscalls/session_gate.S';Name='session-gate';Flags=@('-DDESKTOP_EXTERNAL')},
    @{Source='kernel/loader/external_sbef.S';Name='external-loader';Flags=@()}
)) {
    $obj=Join-Path $output ($unit.Name+'.o')
    & (Join-Path $llvm 'clang.exe') --target=x86_64-unknown-none-elf @($unit.Flags) -c (Join-Path $root $unit.Source) -o $obj
    if ($LASTEXITCODE -ne 0) {throw 'Fallo ensamblado de fixture.'}
    & (Join-Path $llvm 'llvm-objcopy.exe') -O binary --only-section=.text $obj (Join-Path $output ($unit.Name+'.bin'))
    if ($LASTEXITCODE -ne 0) {throw 'Fallo extraccion de fixture.'}
}
$elf=Join-Path $output 'raster.elf'
$sbef=Join-Path $output 'raster.sbef'
& rustc @flags '-Clto=fat' '-Clinker-flavor=ld' "-Clinker=$llvm/ld.lld.exe" "-Clink-arg=-T$PSScriptRoot/guest.ld" "-Clink-arg=$output/portal.o" (Join-Path $PSScriptRoot 'guest.rs') -o $elf
if ($LASTEXITCODE -ne 0) {throw 'Fallo ELF Rust freestanding.'}
& $Python (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1 --size-report --max-file-bytes 16512 --max-mapped-bytes 16384
if ($LASTEXITCODE -ne 0) {throw 'SBEF rechazado; conservar presupuesto.'}
& $Python (Join-Path $root 'tools/boot/doom_qemu.py') $AbiRun $sbef --session-gate (Join-Path $output 'session-gate.bin') --external-loader (Join-Path $output 'external-loader.bin') --rmlui-renderer (Join-Path $output 'expected.bin')
if ($LASTEXITCODE -ne 0) {throw 'Fallo prueba real CPL3.'}
