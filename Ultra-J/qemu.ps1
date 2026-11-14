[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$AbiRun,
    [Parameter(Mandatory)][string]$SplashRun,
    [Parameter(Mandatory)][string]$DesktopRun,
    [string]$Python,
    [string]$Llvm = (Join-Path $env:ProgramFiles 'LLVM/bin')
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
if (-not $Python) {
    $command = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
    $Python = if ($command) { $command.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
$output = (New-Item -ItemType Directory -Force (Join-Path $root 'build/ultra-j')).FullName
$view = Join-Path $output 'panel.ujv'
$object = Join-Path $output 'view.o'
$elf = Join-Path $output 'view.elf'
$sbef = Join-Path $output 'view.sbef'
& $Python -B (Join-Path $PSScriptRoot 'view.py') (Join-Path $PSScriptRoot 'examples/panel.ujh') (Join-Path $PSScriptRoot 'examples/panel.ujc') $view
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion de la vista.' }
& (Join-Path $Llvm 'clang.exe') --target=x86_64-unknown-none-elf -I $output -c (Join-Path $PSScriptRoot 'guest_view.S') -o $object
if ($LASTEXITCODE -ne 0) { throw 'Fallo el ensamblado del presentador de usuario.' }
& (Join-Path $Llvm 'ld.lld.exe') -T (Join-Path $root 'tools/desktop/external.ld') $object -o $elf
if ($LASTEXITCODE -ne 0) { throw 'Fallo el enlace de la vista.' }
& $Python -B (Join-Path $root 'tools/sbef.py') pack $elf $sbef --abi 1 --size-report
if ($LASTEXITCODE -ne 0) { throw 'Fallo la admision HOST de la vista SBEF.' }
& $Python -B (Join-Path $root 'tools/boot/stage_desktop_media.py') $AbiRun $SplashRun $DesktopRun --ultra-j-view $sbef
if ($LASTEXITCODE -ne 0) { throw 'Fallo la comprobacion de la vista en QEMU.' }
