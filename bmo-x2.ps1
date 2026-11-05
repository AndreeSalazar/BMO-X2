# BMO-X2: herramientas host y SUPER GRAFO. No despliega a discos.
[CmdletBinding()]
param(
    [ValidateSet('abrir','resumen','consultar','mapa','comprobar','medir','compilar','preparar-grafo')]
    [string]$Accion = 'resumen',
    [string]$Source,
    [string]$Python,
    [string]$Compiler,
    [string]$SuperGrafo,
    [string]$Consulta = 'resumen',
    [string]$Argumentos
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
if (-not $Python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($pythonCommand) { $pythonCommand.Source } else {
        Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Falta Python. Indicar -Python <ruta>.' }
if (-not $SuperGrafo) {
    $localGrafo = Join-Path $projectRoot 'build/tools/super-grafo/release/ultra-carpetas.exe'
    # Reutiliza el cache local anterior a la normalizacion de nombres, si existe.
    $legacyGrafo = Join-Path $projectRoot 'build/herramientas/super-grafo/release/ultra-carpetas.exe'
    $SuperGrafo = if (Test-Path -LiteralPath $localGrafo -PathType Leaf) { $localGrafo } else {
        if (Test-Path -LiteralPath $legacyGrafo -PathType Leaf) { $legacyGrafo } else {
            Join-Path (Split-Path $projectRoot) 'SUPER GRAFO/ultra-carpetas/target/release/ultra-carpetas.exe'
        }
    }
}
function Invoke-ProjectPython([string]$Operation) {
    & $Python -B (Join-Path $projectRoot 'tools/project.py') $Operation
    if ($LASTEXITCODE -ne 0) { throw "Fallo project.py: $Operation" }
}
if ($Accion -in @('abrir','resumen','consultar','mapa')) {
    if (-not (Test-Path -LiteralPath $SuperGrafo -PathType Leaf)) {
        throw 'Falta el ejecutable de SUPER GRAFO. Construirlo en su proyecto o indicar -SuperGrafo <ruta>.'
    }
}
switch ($Accion) {
    'preparar-grafo' {
        & (Join-Path $projectRoot 'tools/super-grafo.ps1')
    }
    'comprobar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion comprobar -Python $Python -Compiler $Compiler
    }
    'compilar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source $Source -Python $Python -Compiler $Compiler
    }
    'medir' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion medir -Python $Python -Compiler $Compiler
    }
    'resumen' {
        & $SuperGrafo --consulta resumen $projectRoot
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la consulta resumen de SUPER GRAFO.' }
    }
    'consultar' {
        $jsonArguments = $Argumentos
        $psv = $PSVersionTable.PSVersion
        if ($jsonArguments -and ($psv.Major -lt 7 -or ($psv.Major -eq 7 -and $psv.Minor -lt 3))) {
            $jsonArguments = $jsonArguments -replace '"', '\"'
        }
        if ($jsonArguments) { & $SuperGrafo --consulta $Consulta $projectRoot $jsonArguments }
        else { & $SuperGrafo --consulta $Consulta $projectRoot }
        if ($LASTEXITCODE -ne 0) { throw "Fallo la consulta $Consulta de SUPER GRAFO." }
    }
    'mapa' {
        Invoke-ProjectPython 'generar'
        & $SuperGrafo --consulta guardar $projectRoot
        if ($LASTEXITCODE -ne 0) { throw 'SUPER GRAFO no pudo guardar el mapa. Si el ejecutable es anterior a sus fuentes, usar -Accion preparar-grafo.' }
        Invoke-ProjectPython 'ordenar'
    }
    'abrir' {
        Invoke-ProjectPython 'comprobar'
        $workspaceFile = Join-Path $projectRoot 'BMO-X2.sg-workspace'
        if (-not (Test-Path -LiteralPath $workspaceFile -PathType Leaf)) { throw 'Falta BMO-X2.sg-workspace.' }
        Start-Process -FilePath $SuperGrafo -ArgumentList @('--workspace', ('"' + $workspaceFile + '"')) -WorkingDirectory $projectRoot -WindowStyle Normal | Out-Null
        Write-Output 'SUPER GRAFO iniciado con BMO-X2.sg-workspace. La sesion local recuerda vista, panel y pestanas guardadas.'
    }
}
