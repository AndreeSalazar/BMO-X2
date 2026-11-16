# Archive and remove only the four retired BMO-X2 files from A:.
# Linux/ULTRA, EFI/BOOT and the active desktop are outside the deletion list.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$archive=[IO.Path]::GetFullPath((Join-Path $root 'build/archives/retired-bmo-x2'))
if(-not $archive.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archivo fuera del proyecto.'}
if([IO.DriveInfo]::new('A:\').DriveFormat -ne 'FAT32'){throw 'A: no es FAT32.'}
$firmware=(& bcdedit.exe /enum firmware) -join "`n"
if($LASTEXITCODE -ne 0){throw 'No se puede comprobar el firmware.'}
if($firmware.IndexOf('\EFI\BMO-X2\BMO-X2.EFI',[StringComparison]::OrdinalIgnoreCase) -ge 0){throw 'El EFI anterior sigue registrado.'}
if($firmware.IndexOf('\EFI\BMO-X2\DESKTOP.EFI',[StringComparison]::OrdinalIgnoreCase) -lt 0){throw 'Falta la entrada nueva.'}
$manifest=Get-Content -LiteralPath 'A:\BMO-X2\DESKTOP\DEPLOY.JSON' -Raw | ConvertFrom-Json
$active=@{}
foreach($name in @('EFI/BMO-X2/DESKTOP.EFI','BMO-X2/DESKTOP/INICIO.X86','BMO-X2/DESKTOP/DESKTOP.SBF')) {
    $hash=(Get-FileHash -LiteralPath (Join-Path 'A:\' $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if($hash -ne $manifest.Files.$name){throw "Candidato no coincide: $name"}
    $active[$name]=$hash
}
$paths=@('A:\EFI\BMO-X2\BMO-X2.EFI','A:\BMO-X2\INICIO.X86','A:\BMO-X2\DESKTOP.SBF','A:\BMO-X2\BOOTLOG.TXT')
$records=@()
foreach($path in $paths) {
    if(-not (Test-Path -LiteralPath $path)){continue}
    $item=Get-Item -LiteralPath $path
    if($item.PSIsContainer -or $item.FullName -notin $paths -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Solo archivos exactos del perfil retirado.'}
    $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $target=Join-Path $archive (($path.Substring(3)) + '.' + $hash)
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $path -Destination $target -Force
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash){throw 'Archivo no verificado.'}
    $records+=@{Source=$path;Archive=$target;SHA256=$hash;Bytes=$item.Length}
}
# All backups must exist and match before the first removal.
foreach($record in $records) {
    if((Get-FileHash -LiteralPath $record.Source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.SHA256){throw 'Origen cambio durante el archivo.'}
    Remove-Item -LiteralPath $record.Source
}
foreach($name in $active.Keys) {
    if((Get-FileHash -LiteralPath (Join-Path 'A:\' $name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $active[$name]){throw 'Candidato activo alterado.'}
}
New-Item -ItemType Directory -Path $archive -Force | Out-Null
$record=[ordered]@{Schema=1;RemovedFiles=$records;ActiveFilesUnchanged=$active;ExcludedRoots=@('A:\ULTRA','A:\EFI\ULTRA','A:\EFI\BOOT','A:\EFI\ORQUESTADOR');FirmwareModified=$false}
$record | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $archive 'receipt.json') -Encoding UTF8
Write-Output "Retirados $($records.Count) archivos anteriores; archivados en $archive."
Write-Output 'Linux/ULTRA y el escritorio nuevo conservados.'
