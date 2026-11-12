[CmdletBinding()]
param(
    [string]$Python,
    [string]$Qemu,
    [switch]$Play
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
if (-not $Python) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($command) { $command.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
$build = (New-Item -ItemType Directory -Force (Join-Path $root ('build/audio/run-' + [guid]::NewGuid().ToString('N')))).FullName
$source = Join-Path $root 'userspace/services/audio/src/lib.rs'
$library = Join-Path $build 'libbmo_x2_audio.rlib'
$renderer = Join-Path $build 'preview.exe'
$wav = Join-Path $build 'preview.wav'
$flags = @('--edition=2024', '-D', 'warnings', '-C', 'opt-level=2')
& rustc @flags --crate-name bmo_x2_audio --crate-type rlib $source -o $library
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del mezclador.' }
& rustc @flags --extern "bmo_x2_audio=$library" (Join-Path $PSScriptRoot 'audio/preview.rs') -o $renderer
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion de la sonda WAV.' }
& $renderer $wav
if ($LASTEXITCODE -ne 0) { throw 'Fallo la emision WAV.' }

$arguments = @()
if ($Qemu) { $arguments = @('--qemu', (Resolve-Path -LiteralPath $Qemu).Path) }
$report = & $Python -B (Join-Path $PSScriptRoot 'audio/check.py') $wav @arguments
if ($LASTEXITCODE -ne 0) { throw 'Fallo la verificacion de audio.' }
$report | Set-Content -LiteralPath (Join-Path $build 'report.json') -Encoding ascii
$report
Write-Output "WAV: $wav"
if ($Play) {
    $player = New-Object Media.SoundPlayer $wav
    try { $player.PlaySync() }
    finally { $player.Dispose() }
}
