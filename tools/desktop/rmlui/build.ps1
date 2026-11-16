[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'dependencies.lock.json') -Raw | ConvertFrom-Json
foreach ($pin in $lock.dependencies) {
    $dependency = [IO.Path]::GetFullPath((Join-Path $root ('build/deps/' + $pin.folder)))
    $cache = [IO.Path]::GetFullPath((Join-Path $root 'build/deps'))
    if (-not $dependency.StartsWith($cache + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Dependencia fuera del cache.' }
    if (-not (Test-Path -LiteralPath $dependency)) { throw "Falta dependencia fijada: $dependency" }
    $revision = & git -C $dependency rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $revision -ne $pin.Commit) { throw "Revision incorrecta: $dependency" }
    $changes = & git -C $dependency status --porcelain
    if ($changes) { throw "Dependencia modificada: $dependency" }
}
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Falta biblioteca C++/SDK de Visual Studio para el prototipo Windows HOST.' }
Import-Module (Join-Path $vs 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $vs -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'
$clang = Join-Path $env:ProgramFiles 'LLVM/bin/clang-cl.exe'
$output = Join-Path $root 'build/rmlui-host/native'
& cmake -S $PSScriptRoot -B $output -G 'NMake Makefiles' -DCMAKE_BUILD_TYPE=Release "-DCMAKE_C_COMPILER=$clang" "-DCMAKE_CXX_COMPILER=$clang"
if ($LASTEXITCODE -ne 0) { throw 'Fallo configuracion RmlUi.' }
$log = Join-Path $output 'compile.log'
& cmake --build $output *> $log
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $log -Tail 40; throw 'Fallo compilacion RmlUi.' }
Get-Content -LiteralPath $log -Tail 5
Write-Output "HOST DLL: $output/bmo_rmlui_host.dll"
