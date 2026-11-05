$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../paths.ps1')
$root = 'C:\Work\Test Project [x]'
foreach ($case in @(
    @{Path='C:\Work\Test Project [x]\CASM\src\main.c';Want='CASM/src/main.c'},
    @{Path='C:\Work\Test Project [x]\CASM\src\..\catalog.json';Want='CASM/catalog.json'},
    @{Path='c:\work\test project [x]\file.txt';Want='file.txt'}
)) {
    $actual = ConvertTo-ProjectRelativePath -Root $root -Path $case.Path
    if ($actual -cne $case.Want) { throw "Ruta distinta: $actual" }
}
foreach ($path in @('C:\Work\Test Project [x]-other\secret','C:\Work\Test Project [x]\..\secret','D:\external\file',$root)) {
    $rejected = $false
    try { ConvertTo-ProjectRelativePath -Root $root -Path $path | Out-Null }
    catch { $rejected = $true }
    if (-not $rejected) { throw "Se acepto una ruta externa: $path" }
}
Write-Output "GREEN [PATHS] 7 casos; PowerShell $($PSVersionTable.PSVersion)."
