# Inspect a Windows x64 PE with the BMO-X2 HOST and save its intake report.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archivo,
    [switch]$Empaquetar,
    [string]$Manifiesto,
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
$provenanceReport = [ordered]@{
    Status = 'no-declarado'
    ToolchainIdentityAttested = $false
}

if ($Manifiesto) {
    if (-not (Test-Path -LiteralPath $Manifiesto -PathType Leaf)) {
        throw "El manifiesto no existe: $Manifiesto"
    }
    $manifestFile = (Resolve-Path -LiteralPath $Manifiesto).Path
    try {
        $provenance = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "El manifiesto de productor no es JSON valido: $Manifiesto"
    }
    $requiredFields = @('Schema', 'Target', 'Producer', 'Compiler', 'CompilerVersion',
                        'Linker', 'LinkerVersion', 'Options', 'OutputSHA256')
    foreach ($field in $requiredFields) {
        if (-not ($provenance.PSObject.Properties.Name -contains $field)) {
            throw "Falta el campo $field en el manifiesto de productor."
        }
    }
    if ($provenance.Schema -ne 1 -or $provenance.Target -ne 'x86-64') {
        throw 'El manifiesto requiere Schema 1 y Target x86-64.'
    }
    foreach ($field in @('Producer', 'Compiler', 'CompilerVersion', 'Linker', 'LinkerVersion')) {
        if ([string]::IsNullOrWhiteSpace([string]$provenance.$field)) {
            throw "El campo $field del manifiesto no puede estar vacio."
        }
    }
    if ($provenance.Options -isnot [System.Array]) {
        throw 'Options debe ser una lista JSON de argumentos del compilador/enlazador.'
    }
    $declaredHash = [string]$provenance.OutputSHA256
    if ($declaredHash -notmatch '^[0-9A-Fa-f]{64}$' -or $declaredHash.ToLowerInvariant() -ne $sourceHash) {
        throw 'OutputSHA256 del manifiesto no coincide con el PE recibido.'
    }
    $manifestHash = (Get-FileHash -LiteralPath $manifestFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $provenanceReport = [ordered]@{
        Status = 'declarado-hash-coincide-toolchain-no-verificado'
        Manifest = [IO.Path]::GetFileName($manifestFile)
        ManifestSHA256 = $manifestHash
        OutputSHA256Matches = $true
        ToolchainIdentityAttested = $false
        Declaration = $provenance
    }
    $reportPath = Join-Path $reportDirectory ($safeName + '-' + $sourceHash.Substring(0, 12) + '-' +
                                                   $manifestHash.Substring(0, 12) + '.json')
}

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
    Provenance = $provenanceReport
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

Write-Output "HOST PE32+ intake: $inputFile"
Write-Output "SHA-256: $sourceHash"
Write-Output "Procedencia: $($provenanceReport.Status)"
if ($provenanceReport.Declaration) {
    Write-Output "Productor declarado: $($provenanceReport.Declaration.Producer)"
    Write-Output 'El manifiesto coincide con el hash PE; la identidad del toolchain no esta verificada.'
}
Write-Output "Informe: $reportPath"
if ($probe.PSObject.Properties.Name -contains 'CanPack') {
    Write-Output "SBEF del perfil actual: $($probe.CanPack)"
}
if ($probe.PSObject.Properties.Name -contains 'Blockers') {
    foreach ($blocker in $probe.Blockers) {
        Write-Output "Pendiente HOST: $($blocker.Code) / $($blocker.Field) / offset 0x$('{0:X}' -f $blocker.Offset)"
    }
}
if ($probe.PSObject.Properties.Name -contains 'ImportCoverage' -and $probe.ImportCoverage.LibraryCount) {
    foreach ($library in $probe.ImportCoverage.Libraries) {
        $level = if ($library.Level) { "$($library.Level)/$($library.Group)" } else { 'sin clasificar' }
        Write-Output "Dependencia: $($library.DLL) / $level / $($library.PendingSymbols.Count) simbolos pendientes"
    }
    Write-Output "Coincidencias con fixture QEMU: $($probe.ImportCoverage.FixtureSymbolCount)"
    Write-Output "El informe JSON contiene el inventario completo de simbolos."
}
if ($probe.PSObject.Properties.Name -contains 'ImportInventoryError') {
    Write-Output "Inventario IAT incompleto: $($probe.ImportInventoryError.Code) / $($probe.ImportInventoryError.Field)"
}
if ($probe.PSObject.Properties.Name -contains 'UnwindInventory') {
    $unwind = $probe.UnwindInventory
    Write-Output "Unwind: $($unwind.FunctionCount) entradas / $($unwind.V1Handlers.Count) destinos de handler v1 / $($unwind.V1ChainedCount) encadenadas v1"
} elseif ($probe.PSObject.Properties.Name -contains 'UnwindInventoryError') {
    Write-Output "Inventario unwind incompleto: $($probe.UnwindInventoryError.Code) / $($probe.UnwindInventoryError.Field)"
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
