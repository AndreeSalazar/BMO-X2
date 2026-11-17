# Read-only verification by default; -Apply restores the saved desktop files.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Run,[switch]$Apply)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$runPath=(Get-Item -LiteralPath $Run).FullName
if((Split-Path $runPath -Parent) -ne (Join-Path $root 'build/CASM')){throw 'Run fuera del proyecto.'}
$record=Get-Content -LiteralPath (Join-Path $runPath 'fat32-deploy.json') -Raw | ConvertFrom-Json
$names=@('EFI/BMO-X2/DESKTOP.EFI','BMO-X2/DESKTOP/INICIO.X86','BMO-X2/DESKTOP/DESKTOP.SBF')
if(@($record.PreviousFiles.PSObject.Properties).Count -ne 3){throw 'Falta el respaldo completo de tres archivos.'}
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $runPath 'fat32-backups'))+'\'
foreach($name in $names) {
    $old=$record.PreviousFiles.$name
    if(-not $old){throw 'Respaldo incompleto.'}
    $source=Get-Item -LiteralPath $old.Archive
    if(-not $source.FullName.StartsWith($archiveRoot,[StringComparison]::OrdinalIgnoreCase) -or
        ($source.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $old.SHA256){throw 'Respaldo fuera de alcance o alterado.'}
    $active=(Get-FileHash -LiteralPath (Join-Path 'A:\' $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    # Also accept an interrupted restore, but never overwrite an unknown file.
    if($active -ne $record.Files.$name -and $active -ne $old.SHA256){throw "Archivo activo desconocido: $name"}
}
if(-not $Apply){Write-Output 'Respaldo completo y hashes correctos. Usar -Apply para restaurar.';return}
if([IO.DriveInfo]::new('A:\').DriveFormat -ne 'FAT32'){throw 'A: no es FAT32.'}
foreach($name in $names) {
    $old=$record.PreviousFiles.$name
    $target=Join-Path 'A:\' $name
    $temp=$target+'.restore-'+[guid]::NewGuid().ToString('N')
    Copy-Item -LiteralPath $old.Archive -Destination $temp
    if((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant() -ne $old.SHA256){throw 'Copia de restauracion alterada.'}
    Move-Item -LiteralPath $temp -Destination $target -Force
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $old.SHA256){throw 'Restauracion no verificada.'}
}
$previousReceipt=Join-Path $runPath 'fat32-backups/DEPLOY.before.json'
if(Test-Path -LiteralPath $previousReceipt){Copy-Item -LiteralPath $previousReceipt -Destination 'A:\BMO-X2\DESKTOP\DEPLOY.JSON' -Force}
Write-Output 'Escritorio anterior restaurado y verificado. Firmware y Linux sin cambios.'
