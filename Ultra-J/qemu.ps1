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
$action = Join-Path $output 'panel-action.ujb'
& $Python -B (Join-Path $PSScriptRoot 'package.py') (Join-Path $PSScriptRoot 'examples/panel') $output
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del paquete del panel.' }
$sbef = & (Join-Path $PSScriptRoot 'targets/x86_64/build.ps1') -View $view -Action $action -Python $Python -Llvm $Llvm
& $Python -B (Join-Path $root 'tools/boot/stage_desktop_media.py') $AbiRun $SplashRun $DesktopRun --ultra-j-view $sbef
if ($LASTEXITCODE -ne 0) { throw 'Fallo la comprobacion de la vista en QEMU.' }
