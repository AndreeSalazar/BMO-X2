[CmdletBinding()]
param(
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin'),
    [string]$Python
)
$ErrorActionPreference = 'Stop'
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
$flags = @('--edition=2024', '--target', $target, '-D', 'warnings', '-C', 'panic=abort',
           '-C', 'opt-level=s', '-C', 'relocation-model=static', '-C', 'force-unwind-tables=no')
& rustc @flags --crate-name bmo_x2_desktop --crate-type rlib (Join-Path $desktop 'src/lib.rs') -o $library
if ($LASTEXITCODE -ne 0) { throw 'Fallo el build Rust. Verifica rustup target add x86_64-unknown-none.' }
& (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -c (Join-Path $root 'userspace/runtime/abi/portal.S') -o $portal
if ($LASTEXITCODE -ne 0) { throw 'Fallo el stub ABI.' }
$linkFlags = @('-C', "linker=$linker", '-C', 'linker-flavor=ld', '-C', 'lto=fat',
               '-C', "link-arg=-T$linkScript", '-C', "link-arg=$portal")
& rustc @flags @linkFlags --crate-name desktop_probe --extern "bmo_x2_desktop=$library" (Join-Path $desktop 'src/bin/desktop_probe.rs') -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace ELF del escritorio.' }
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $image --abi 1
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST del escritorio.' }
Write-Output "SBEF: $image"
