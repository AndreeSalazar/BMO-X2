# Register the already validated desktop candidate as a separate UEFI entry.
# Run in elevated Windows PowerShell 5.1. Never selects the next boot.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$receipt=Join-Path $root 'build/rmlui-native/firmware-desktop.json'
$name='BMO-X2 Desktop (RmlUi)'
$path='\EFI\BMO-X2\DESKTOP.EFI'
$manifest=Get-Content -LiteralPath 'A:\BMO-X2\DESKTOP\DEPLOY.JSON' -Raw | ConvertFrom-Json
if ([IO.DriveInfo]::new('A:\').DriveFormat -ne 'FAT32') {throw 'A: no es FAT32.'}
foreach($file in @('EFI/BMO-X2/DESKTOP.EFI','BMO-X2/DESKTOP/INICIO.X86','BMO-X2/DESKTOP/DESKTOP.SBF')) {
    if ((Get-FileHash -LiteralPath (Join-Path 'A:\' $file) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.Files.$file) {
        throw "Archivo no coincide con el candidato verificado: $file"
    }
}
function Invoke-Bcd([string[]]$BcdArgs) {
    $output=& bcdedit.exe @BcdArgs 2>&1
    if($LASTEXITCODE -ne 0){throw ($output -join "`n")}
    return ($output -join "`n")
}
$before=Invoke-Bcd @('/enum','firmware')
$blocks=$before -split '(?:\r?\n){2,}'
$existing=@($blocks | Where-Object {$_ -match ('(?m)^description\s+'+[regex]::Escape($name)+'\s*$')})
$created=$false
if($existing.Count -gt 1){throw 'Mas de una entrada del candidato; revisar antes de registrar.'}
if($existing.Count -eq 1) {
    $id=[regex]::Match($existing[0],'\{[0-9a-fA-F-]{36}\}').Value
    if(-not $id -or $existing[0] -notmatch '(?im)^device\s+partition=A:\\?\s*$' -or
        $existing[0] -notmatch ('(?im)^path\s+'+[regex]::Escape($path)+'\s*$')) {throw 'Entrada existente incompatible.'}
} else {
    $legacy=@($blocks | Where-Object {$_ -match '(?m)^description\s+BMO-X2\s*$' -and $_ -match '(?im)^device\s+partition=A:\\?\s*$'})
    if($legacy.Count -gt 1){throw 'Mas de una entrada anterior; revisar antes de registrar.'}
    # The retired entry/files may already have been cleaned. Copying bootmgr
    # creates a distinct object; its device/path are replaced below.
    $legacyId=if($legacy.Count -eq 1){[regex]::Match($legacy[0],'\{[0-9a-fA-F-]{36}\}').Value}else{'{bootmgr}'}
    if(-not $legacyId){throw 'Falta identificador de la entrada anterior.'}
    $copy=Invoke-Bcd @('/copy',$legacyId,'/d',$name)
    $id=[regex]::Match($copy,'\{[0-9a-fA-F-]{36}\}').Value
    if(-not $id){throw 'No se obtuvo el identificador nuevo.'}
    $created=$true
    try {
        Invoke-Bcd @('/set',$id,'device','partition=A:') | Out-Null
        Invoke-Bcd @('/set',$id,'path',$path) | Out-Null
        Invoke-Bcd @('/set','{fwbootmgr}','displayorder',$id,'/addlast') | Out-Null
    } catch {
        Invoke-Bcd @('/delete',$id) | Out-Null
        throw
    }
}
$after=Invoke-Bcd @('/enum','firmware')
$entry=Invoke-Bcd @('/enum',$id)
if($entry -notmatch [regex]::Escape($path) -or $after -notmatch [regex]::Escape($id)){throw 'No se confirma el registro UEFI.'}
$record=[ordered]@{Schema=1;Name=$name;Identifier=$id;Device='partition=A:';Path=$path;Created=$created;
    Placement='Last; previous entries preserved';BootSelected=$false;PhysicalBootVerified=$false;
    CandidateRun=$manifest.Run;Before=$before;After=$after}
New-Item -ItemType Directory -Path (Split-Path $receipt -Parent) -Force | Out-Null
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding UTF8
Write-Output "Entrada UEFI disponible: $name"
Write-Output "Archivo: $path"
Write-Output 'Al reiniciar, elegir ese nombre en el menu de arranque. No se reinicio ni se cambio el siguiente arranque.'
