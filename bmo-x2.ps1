# BMO-X2: herramientas host y SUPER GRAFO. No despliega a discos.
[CmdletBinding()]
param(
    [ValidateSet('abrir','resumen','consultar','mapa','comprobar','medir','compilar','genesis','despertar','parada','detectar','pila','excepcion','memoria','marcos','paginacion','aislamiento','abi','revocar','pesos','gato','gato-hd','leer-hex','preparar-grafo')]
    [string]$Accion = 'resumen',
    [string]$Source,
    [ValidateSet("metal64-0.2","ring0-stop-0.1","ring0-cpu-0.1","ring0-context-0.1","ring0-fault-0.1","ring0-memory-0.1","ring0-frame-cycle-0.1","ring0-paging-0.1","ring0-user-fault-0.1","ring0-abi-probe-0.1","ring0-hot-unmap-0.1","ring0-splash-0.1","ring0-splash-hd-0.1")][string]$Profile = "metal64-0.2",
    [string]$Run,
    [string]$Python,
    [string]$Compiler,
    [ValidateSet('qemu64','Nehalem')][string]$Cpu = 'qemu64',
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
    'revocar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/mm/virtual/revoke/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-hot-unmap-0.1 -Wake -Cpu $Cpu
    }
    'abi' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/syscalls/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-abi-probe-0.1 -Wake -Cpu $Cpu
    }
    'aislamiento' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/mm/user/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-user-fault-0.1 -Wake -Cpu $Cpu
    }
    'paginacion' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/mm/virtual/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-paging-0.1 -Wake -Cpu $Cpu
    }
    'marcos' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/mm/physical/lifecycle/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-frame-cycle-0.1 -Wake -Cpu $Cpu
    }
    'memoria' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/mm/physical/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-memory-0.1 -Wake -Cpu $Cpu
    }
    'pesos' {
        & $Python -B (Join-Path $projectRoot 'tools/boot/weights.py')
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la medicion de artefactos QEMU.' }
    }
    'excepcion' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/arch/x86_64/exceptions/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-fault-0.1 -Wake -Cpu $Cpu
    }
    'gato-hd' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/splash/hd/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-splash-hd-0.1 -Wake -Cpu $Cpu
    }
    'gato' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/splash/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-splash-0.1 -Wake -Cpu $Cpu
    }
    'pila' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/context/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-context-0.1 -Wake -Cpu $Cpu
    }
    'detectar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/arch/x86_64/cpu/identify.casm') -Python $Python -Compiler $Compiler -Profile ring0-cpu-0.1 -Wake -Cpu $Cpu
    }
    'parada' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/stop/main.casm') -Python $Python -Compiler $Compiler -Profile ring0-stop-0.1 -Wake
    }
    'despertar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/genesis/main.casm') -Python $Python -Compiler $Compiler -Genesis -Wake
    }
    'genesis' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source (Join-Path $projectRoot 'kernel/boot/genesis/main.casm') -Python $Python -Compiler $Compiler -Genesis
        & $Python -B (Join-Path $projectRoot 'tools/genesis_graph.py')
        if ($LASTEXITCODE -ne 0) { throw 'Fallo el guardado del grafo Genesis.' }
    }
    'leer-hex' {
        if (-not $Run) { throw 'Indicar -Run <build/CASM/run-...>.' }
        & $Python -B (Join-Path $projectRoot 'tools/hex_report.py') $Run
        if ($LASTEXITCODE -ne 0) { throw 'No se genera lectura de una emision rechazada.' }
    }
    'preparar-grafo' {
        & (Join-Path $projectRoot 'tools/super-grafo.ps1')
    }
    'comprobar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion comprobar -Python $Python -Compiler $Compiler
    }
    'compilar' {
        Invoke-ProjectPython 'comprobar'
        & (Join-Path $projectRoot 'tools/host.ps1') -Accion compilar -Source $Source -Profile $Profile -Python $Python -Compiler $Compiler
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
