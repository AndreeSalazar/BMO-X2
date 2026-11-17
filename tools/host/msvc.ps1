# Inspect a Windows x64 PE with the BMO-X2 HOST and save its intake report.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archivo,
    [switch]$Empaquetar,
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$inputFile = (Resolve-Path -LiteralPath $Archivo).Path
if (-not (Test-Path -LiteralPath $inputFile -PathType Leaf)) {
    throw "El archivo no existe: $Archivo"
}

if (-not $Python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($pythonCommand) { $pythonCommand.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'No se encontro Python. Indica -Python <ruta>.'
}

$reportDirectory = Join-Path $projectRoot 'build/msvc-intake'
New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
$sourceHash = (Get-FileHash -LiteralPath $inputFile -Algorithm SHA256).Hash.ToLowerInvariant()
$baseName = [IO.Path]::GetFileNameWithoutExtension($inputFile)
$safeName = [regex]::Replace($baseName, '[^A-Za-z0-9._-]', '_')
$reportPath = Join-Path $reportDirectory ($safeName + '-' + $sourceHash.Substring(0, 12) + '.json')
$cli = Join-Path $projectRoot 'tools/sbef.py'

function Invoke-HostJson([string[]]$Arguments) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & $Python -B $cli @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    $lines = @($output | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            $_.Exception.Message
        } else {
            [string]$_
        }
    })
    [PSCustomObject]@{ ExitCode = $exitCode; Text = ($lines -join [Environment]::NewLine).Trim() }
}

$probeResult = Invoke-HostJson @('--json-errors', 'probe', $inputFile)
$probeExit = $probeResult.ExitCode
$probeText = $probeResult.Text
try {
    $probe = $probeText | ConvertFrom-Json -ErrorAction Stop
} catch {
    throw "HOST no pudo producir un diagnostico JSON. $probeText"
}

$report = [ordered]@{
    Schema = 1
    Source = [IO.Path]::GetFileName($inputFile)
    SourceBytes = (Get-Item -LiteralPath $inputFile).Length
    SourceSHA256 = $sourceHash
    ProbeExitCode = $probeExit
    Probe = $probe
    Package = $null
}

if ($Empaquetar -and $probeExit -eq 0 -and $probe.CanPack) {
    $packagePath = Join-Path $reportDirectory ($safeName + '-' + $sourceHash.Substring(0, 12) + '.SBEF')
    $packageResult = Invoke-HostJson @('--json-errors', 'pack', $inputFile, $packagePath,
                                       '--abi', '1', '--size-report')
    $packageExit = $packageResult.ExitCode
    $packageText = $packageResult.Text
    try {
        $package = $packageText | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "HOST no pudo producir el resultado de empaquetado en JSON. $packageText"
    }
    $report.Package = [ordered]@{
        ExitCode = $packageExit
        Path = if ($packageExit -eq 0) { $packagePath } else { $null }
        Result = $package
    }
} elseif ($Empaquetar) {
    $report.Package = [ordered]@{
        ExitCode = 1
        Path = $null
        Result = 'HOST rechazo el perfil. Consulta Probe.Blockers.'
    }
}

$json = $report | ConvertTo-Json -Depth 32
[IO.File]::WriteAllText($reportPath, $json + [Environment]::NewLine, [Text.Encoding]::UTF8)

Write-Output "HOST MSVC intake: $inputFile"
Write-Output "SHA-256: $sourceHash"
Write-Output "Informe: $reportPath"
if ($probe.PSObject.Properties.Name -contains 'CanPack') {
    Write-Output "SBEF del perfil actual: $($probe.CanPack)"
}
if ($probe.PSObject.Properties.Name -contains 'Blockers') {
    foreach ($blocker in $probe.Blockers) {
        Write-Output "Pendiente HOST: $($blocker.Code) / $($blocker.Field) / offset 0x$('{0:X}' -f $blocker.Offset)"
    }
}
if ($probe.PSObject.Properties.Name -contains 'Imports') {
    foreach ($library in $probe.Imports) {
        Write-Output "Dependencia: $($library.DLL) / $($library.Symbols.Count) simbolos"
    }
    Write-Output "El informe JSON contiene el inventario completo de simbolos."
}
if ($probe.PSObject.Properties.Name -contains 'ImportInventoryError') {
    Write-Output "Inventario IAT incompleto: $($probe.ImportInventoryError.Code) / $($probe.ImportInventoryError.Field)"
}
if ($report.Package.Path) {
    Write-Output "SBEF creado: $($report.Package.Path)"
} elseif ($Empaquetar) {
    Write-Output 'SBEF no creado. HOST registro las condiciones pendientes en el informe.'
}

if ($probeExit -ne 0) { throw "HOST rechazo el archivo. Consulta Probe en $reportPath" }
if ($Empaquetar -and -not $report.Package.Path) {
    throw "HOST no genero un SBEF para este perfil. Consulta Probe.Blockers en $reportPath"
}
