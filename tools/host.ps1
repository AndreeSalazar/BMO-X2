[CmdletBinding()]
param(
    [ValidateSet('comprobar','compilar','medir')][string]$Accion,
    [string]$Python,
    [string]$Compiler,
    [string]$Source,
    [switch]$Genesis,
    [switch]$Wake,
    [ValidateSet('qemu64','Nehalem')][string]$Cpu = 'qemu64',
    [ValidateSet("metal64-0.2","ring0-stop-0.1","ring0-cpu-0.1","ring0-context-0.1","ring0-fault-0.1","ring0-memory-0.1","ring0-frame-cycle-0.1","ring0-splash-0.1","ring0-splash-hd-0.1")][string]$Profile = "metal64-0.2"
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
. (Join-Path $PSScriptRoot 'paths.ps1')
if (-not $Compiler) { $Compiler = Join-Path $env:ProgramFiles 'LLVM/bin/clang.exe' }
if (-not (Test-Path -LiteralPath $Compiler -PathType Leaf)) { throw 'Falta Clang. Indicar -Compiler <ruta>.' }
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Falta Python. Usar bmo-x2.ps1.' }
$outputDir = Join-Path $projectRoot 'build/CASM/host'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
& $Python -B (Join-Path $projectRoot 'CASM/catalog.py') generate
if ($LASTEXITCODE -ne 0) { throw 'Catalogo CASM rechazado; no se construye ni publica.' }
$temporaryExe = Join-Path $outputDir 'casmc.build.exe'
$compilerExe = Join-Path $outputDir 'casmc.exe'
$sourceManifest = Get-Content -LiteralPath (Join-Path $projectRoot 'CASM/sources.json') -Raw | ConvertFrom-Json
if ($sourceManifest.schema -ne 1 -or $sourceManifest.target -ne 'x86-64') { throw 'Manifest CASM incompatible.' }
$sources = @($sourceManifest.c_sources) | ForEach-Object { Join-Path $projectRoot "CASM/$_" }
$flags = @('-std=c11','-D_CRT_SECURE_NO_WARNINGS','-Wall','-Wextra','-Werror','-pedantic','-O2')
& $Compiler @flags @sources -o $temporaryExe
if ($LASTEXITCODE -ne 0) { throw 'Fallo la semilla C de CASM. No se ejecuta el binario anterior.' }
Move-Item -LiteralPath $temporaryExe -Destination $compilerExe -Force
$version = (& $Compiler --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'No se pudo identificar Clang.' }
$inputs = @($sources) + @(@($sourceManifest.headers) + @($sourceManifest.inputs) | ForEach-Object { Join-Path $projectRoot "CASM/$_" }) + (Join-Path $projectRoot 'CASM/sources.json')
$hashes = $inputs | ForEach-Object {
    [ordered]@{ruta=(ConvertTo-ProjectRelativePath -Root $projectRoot -Path $_);sha256=(Get-FileHash -LiteralPath $_).Hash.ToLowerInvariant()}
}
$toolchain = [ordered]@{schema=1;host='Windows';powershell=$PSVersionTable.PSVersion.ToString();clr=[Environment]::Version.ToString();target='x86-64';profiles=@('metal64-0.2','ring0-stop-0.1','ring0-cpu-0.1','ring0-context-0.1','ring0-fault-0.1','ring0-memory-0.1','ring0-frame-cycle-0.1','ring0-splash-0.1','ring0-splash-hd-0.1');compiler=$version;flags=$flags;sources=$hashes;executable_sha256=(Get-FileHash -LiteralPath $compilerExe).Hash.ToLowerInvariant()}
$toolchain | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputDir 'toolchain.json') -Encoding utf8
$version | Set-Content -LiteralPath (Join-Path $outputDir 'toolchain.txt') -Encoding utf8
if ($Accion -eq 'comprobar') {
    & (Join-Path $PSScriptRoot 'tests/paths.ps1')
    & $Python -B (Join-Path $projectRoot 'CASM/tests/test_catalog.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el banco del catalogo CASM.' }
    & $Python -B (Join-Path $projectRoot 'CASM/test.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el banco CASM.' }
    & $Python -B (Join-Path $projectRoot 'CASM/tests/test_stop.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el perfil privilegiado ring0-stop.' }
    & $Python -B (Join-Path $projectRoot 'CASM/tests/test_splash.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la comprobacion del splash Ring 0.' }
    $report = Get-Content -LiteralPath (Join-Path $projectRoot 'build/CASM/test-results.json') -Raw | ConvertFrom-Json
    Write-Output "CASM HOST: $($report.Passed)/$($report.Total) aprobados; $(@($report.Skipped).Count) omitidos. No acredita QEMU ni metal."
    $workspaceExe = Join-Path $outputDir 'workspace.exe'
    & $Compiler @flags (Join-Path $projectRoot 'CASM/tests/workspace.c') (Join-Path $projectRoot 'CASM/src/model/storage.c') -o $workspaceExe
    if ($LASTEXITCODE -ne 0) { throw 'Fallo el banco del almacenamiento acotado.' }
    $workspaceReport = & $workspaceExe
    if ($LASTEXITCODE -ne 0) { throw 'No se cumplen los limites del almacenamiento.' }
    $workspaceReport | Set-Content -LiteralPath (Join-Path $outputDir 'workspace.json') -Encoding utf8
    Write-Output $workspaceReport
    return
}
if ($Accion -eq 'medir') {
    & $Python -B (Join-Path $projectRoot 'CASM/tests/maturity.py') --cc $Compiler --compiler $compilerExe
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la comparacion de CASM con la base fijada.' }
    return
}
if (-not $Source) { $Source = Join-Path $projectRoot 'CASM/examples/hello.casm' }
$sourceFile = Get-Item -LiteralPath $Source
if (-not ($sourceFile -is [IO.FileInfo]) -or ($sourceFile.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'La fuente debe ser un archivo regular.'
}
$run = Join-Path $projectRoot ('build/CASM/run-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $run | Out-Null
$frozen = Join-Path $run 'source.casm'
$hex = Join-Path $run 'program.hex'
$ir = Join-Path $run 'program.ir.json'
$log = Join-Path $run 'registro.txt'
Copy-Item -LiteralPath $sourceFile.FullName -Destination $frozen
$sourceFile.FullName | Set-Content -LiteralPath (Join-Path $run 'origen.txt') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $outputDir 'toolchain.txt') -Destination (Join-Path $run 'toolchain.txt')
Copy-Item -LiteralPath (Join-Path $outputDir 'toolchain.json') -Destination (Join-Path $run 'toolchain.json')
Copy-Item -LiteralPath (Join-Path $projectRoot 'CASM/catalog.json') -Destination (Join-Path $run 'catalog.json')
$Profile | Set-Content -LiteralPath (Join-Path $run 'profile.txt') -Encoding utf8
$profileArgs = if ($Profile -ne 'metal64-0.2') { @('--profile', $Profile) } else { @() }
$verifier = if ($Profile -in @('ring0-splash-0.1','ring0-splash-hd-0.1')) { 'CASM/splash_verify.py' } elseif ($Profile -ne 'metal64-0.2') { 'CASM/stop_verify.py' } else { 'CASM/verify.py' }
[string[]]$verifyArgs = if ($Profile -eq 'ring0-cpu-0.1') { '--identify' } elseif ($Profile -eq 'ring0-context-0.1') { '--context' } elseif ($Profile -eq 'ring0-fault-0.1') { '--fault' } elseif ($Profile -eq 'ring0-memory-0.1') { '--memory' } elseif ($Profile -eq 'ring0-frame-cycle-0.1') { '--frame-cycle' } elseif ($Profile -eq 'ring0-splash-hd-0.1') { '--hd' }
& $compilerExe @profileArgs $frozen $hex $ir 2>&1 | Tee-Object -FilePath $log
if ($LASTEXITCODE -ne 0) { throw "Fuente rechazada. No se publico INICIO.X86. Run: $run" }
& $Python -B (Join-Path $projectRoot $verifier) $frozen $hex $ir --packet (Join-Path $run 'INICIO.X86') --report (Join-Path $run 'verified.json') @verifyArgs 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { throw "Emision rechazada. Run: $run" }
Write-Output "HOST: HEX, IR y paquete verificados en $run"
& $Python -B (Join-Path $projectRoot 'tools/hex_report.py') $run
if ($LASTEXITCODE -ne 0) { throw 'Fallo la lectura comprobada del HEX.' }
if ($Genesis) {
    & $Python -B (Join-Path $projectRoot 'tools/genesis.py') $run
    if ($LASTEXITCODE -ne 0) { throw 'Genesis no cumple vector, paquete o presupuesto.' }
}
if ($Wake) {
    $shellName = if ($PSVersionTable.PSVersion.Major -le 5) { 'powershell.exe' } else { 'pwsh.exe' }
    $shellExe = Join-Path $PSHOME $shellName
    $wakeArgs = if ($Profile -in @('ring0-cpu-0.1','ring0-splash-0.1','ring0-splash-hd-0.1')) { @('--cases','normal','--cpu',$Cpu) } else { @() }
    if ($Profile -in @('ring0-context-0.1','ring0-fault-0.1','ring0-memory-0.1','ring0-frame-cycle-0.1')) { $wakeArgs = @('--cases','normal','contexto','--cpu',$Cpu) }
    & $Python -B (Join-Path $projectRoot 'tools/boot/wake.py') $run --powershell $shellExe --profile $Profile @wakeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la prueba en QEMU. Consultar el run conservado.' }
    if ($Profile -in @('ring0-cpu-0.1','ring0-context-0.1','ring0-fault-0.1','ring0-memory-0.1','ring0-frame-cycle-0.1','ring0-splash-0.1','ring0-splash-hd-0.1')) { return }
    & $Python -B (Join-Path $projectRoot 'tools/boot/publish.py') $run
    if ($LASTEXITCODE -ne 0) { throw 'La prueba termino pero no se pudo publicar evidencia comprobada.' }
}
