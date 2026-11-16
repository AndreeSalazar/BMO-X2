$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$cache = [IO.Path]::GetFullPath((Join-Path $root 'build/deps'))
New-Item -ItemType Directory -Force -Path $cache | Out-Null
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'dependencies.lock.json') -Raw | ConvertFrom-Json
foreach ($entry in $lock.dependencies) {
    $destination = [IO.Path]::GetFullPath((Join-Path $cache $entry.folder))
    if (-not $destination.StartsWith($cache + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta de dependencia fuera del cache.' }
    if (-not (Test-Path -LiteralPath $destination)) {
        & git clone --depth 1 --branch $entry.tag $entry.repository $destination
        if ($LASTEXITCODE -ne 0) { throw "No se pudo descargar $($entry.name)." }
    }
    $actual = & git -C $destination rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actual -ne $entry.commit) { throw "Revision no admitida: $($entry.name)." }
}
