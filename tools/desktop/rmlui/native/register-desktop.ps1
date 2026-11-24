# Register a validated desktop candidate as a separate UEFI entry.
# Run in elevated Windows PowerShell 5.1. Never selects the next boot.
[CmdletBinding()]
param([switch]$NvidiaProbe,[switch]$StorageHandoff,[switch]$Check,[switch]$AmdviMmio,[switch]$PhysicalFwsecTrial)
$ErrorActionPreference='Stop'
if (($StorageHandoff -or $AmdviMmio) -and -not $NvidiaProbe) { throw 'La variante requiere -NvidiaProbe.' }
if ($PhysicalFwsecTrial -and (-not $AmdviMmio -or $StorageHandoff)) { throw 'FWSEC requiere -AmdviMmio y -NvidiaProbe.' }
$storageProfile=[bool]($StorageHandoff -or $AmdviMmio)
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$dataFolder=if($PhysicalFwsecTrial){'BMO-X2/GPU-FW'}elseif($AmdviMmio){'BMO-X2/GPU-MM'}elseif($NvidiaProbe){'BMO-X2/GPU'}else{'BMO-X2/DESKTOP'}
$bootFile=if($PhysicalFwsecTrial){'EFI/BMO-X2/RTX-FWSEC.EFI'}elseif($AmdviMmio){'EFI/BMO-X2/AMDVI-MMIO.EFI'}elseif($NvidiaProbe){'EFI/BMO-X2/NVIDIA.EFI'}else{'EFI/BMO-X2/DESKTOP.EFI'}
$receiptName=if($PhysicalFwsecTrial){'firmware-rtx-fwsec.json'}elseif($AmdviMmio){'firmware-amdvi-mmio.json'}elseif($StorageHandoff){'firmware-storage-handoff.json'}elseif($NvidiaProbe){'firmware-nvidia.json'}else{'firmware-desktop.json'}
$receipt=Join-Path $root "build/rmlui-native/$receiptName"
$name=if($PhysicalFwsecTrial){'BMO-X2 (RTX FWSEC)'}elseif($AmdviMmio){'BMO-X2 (AMD-Vi registros)'}elseif($StorageHandoff){'BMO-X2 (DMA SATA-NVMe)'}elseif($NvidiaProbe){'BMO-X2 (con NVIDIA)'}else{'BMO-X2 (Original)'}
$path='\'+$bootFile.Replace('/','\')
$manifest=Get-Content -LiteralPath (Join-Path 'A:\' "$dataFolder/DEPLOY.JSON") -Raw | ConvertFrom-Json
if ([IO.DriveInfo]::new('A:\').DriveFormat -ne 'FAT32') {throw 'A: no es FAT32.'}
$files=@($bootFile,"$dataFolder/INICIO.X86","$dataFolder/DESKTOP.SBF")
if($NvidiaProbe) {
    if ($manifest.BootFile -ne $path -or $manifest.Run -notmatch '^run-rmlui-media-[0-9a-f]{12}$') {
        throw 'DEPLOY.JSON no identifica un candidato NVIDIA verificado.'
    }
    $runPath=Join-Path $root "build/CASM/$($manifest.Run)"
    $proof=Get-Content -LiteralPath (Join-Path $runPath 'media/manifest.json') -Raw | ConvertFrom-Json
    $normal=$proof.Cases | Where-Object { $_.Case -eq 'normal' } | Select-Object -First 1
    $caseCount=if($storageProfile){3}else{2}
    if ($proof.run -ne $manifest.Run -or $proof.Passed -ne $caseCount -or $proof.Total -ne $caseCount -or
        -not $proof.nvidia_pci_probe -or -not $normal.NvidiaPciProbeVerified) {
        throw 'Falta la prueba QEMU del candidato NVIDIA.'
    }
    if ($storageProfile -ne [bool]$proof.storage_quiesce_metal -or ($storageProfile -and
        (-not $normal.StorageQuiesceSkippedVerified -or -not $normal.GspFwsecExcluded -or $proof.amdvi_guest_dma))) {
        throw 'El candidato no acredita la entrega fisica de almacenamiento.'
    }
    if ([bool]$AmdviMmio -ne [bool]$proof.amdvi_physical_mmio_test -or ($AmdviMmio -and
        (-not $normal.PhysicalMmioExcluded -or -not $normal.PhysicalMmioReportVerified -or
         $proof.physical_dma_translation_enabled -or $proof.nvidia_dma_grant))) {
        throw 'Falta verificar el informe de registros AMD-Vi y su exclusion en QEMU.'
    }
    if ([bool]$PhysicalFwsecTrial -ne [bool]$proof.physical_fwsec_trial -or ($PhysicalFwsecTrial -and
        (-not $manifest.PhysicalFwsecTrial -or -not $normal.PhysicalFwsecStatusExportVerified -or
         -not $normal.PhysicalLpcCommandExcluded -or -not $normal.PhysicalFwsecLaunchExcluded))) {
        throw 'Falta verificar el candidato FWSEC separado y su informe.'
    }
    if($storageProfile) { $files += "$dataFolder/GSP.BIN" }
    foreach($file in $files) {
        if ($manifest.Files.$file -ne $proof.files.$file) {throw "Huella distinta del ensayo QEMU: $file"}
    }
}
foreach($file in $files) {
    if ((Get-FileHash -LiteralPath (Join-Path 'A:\' $file) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.Files.$file) {
        throw "Archivo no coincide con el candidato verificado: $file"
    }
}
if($Check) {
    Write-Output "Archivos verificados para la entrada UEFI: $name"
    return
}
function Invoke-Bcd([string[]]$BcdArgs) {
    $output=& bcdedit.exe @BcdArgs 2>&1
    if($LASTEXITCODE -ne 0){throw ($output -join "`n")}
    return ($output -join "`n")
}
function Get-FirmwareOrder([string]$Output) {
    $order=[regex]::Match($Output,'(?im)^displayorder[^\S\r\n]+[^\r\n]+(?:\r?\n[ \t]+\{[^\r\n]+)*').Value
    if(-not $order){throw 'No se puede leer el orden de arranque UEFI.'}
    [regex]::Matches($order,'\{[^}]+\}') | ForEach-Object Value
}
$before=Invoke-Bcd @('/enum','firmware')
$orderBefore=@(Get-FirmwareOrder (Invoke-Bcd @('/enum','{fwbootmgr}')))
$blocks=$before -split '(?:\r?\n){2,}'
$names=@($name)
if (-not $NvidiaProbe) { $names+='BMO-X2 Desktop (RmlUi)' }
$description='(?m)^description[^\S\r\n]+('+(($names | ForEach-Object {[regex]::Escape($_)}) -join '|')+')[^\S\r\n]*\r?$'
$existing=@($blocks | Where-Object {$_ -match $description})
$created=$false
if($existing.Count -gt 1){throw 'Mas de una entrada del candidato; revisar antes de registrar.'}
if($existing.Count -eq 1) {
    $name=[regex]::Match($existing[0],$description).Groups[1].Value
    $id=[regex]::Match($existing[0],'\{[0-9a-fA-F-]{36}\}').Value
    if(-not $id -or $existing[0] -notmatch '(?im)^device\s+partition=A:\\?\s*$' -or
        $existing[0] -notmatch ('(?im)^path\s+'+[regex]::Escape($path)+'\s*$')) {throw 'Entrada existente incompatible.'}
    if($id -notin $orderBefore){throw 'La entrada existe fuera del menu de arranque UEFI.'}
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
        $orderAfter=@(Get-FirmwareOrder (Invoke-Bcd @('/enum','{fwbootmgr}')))
        if (($orderAfter -join ' ') -ne (($orderBefore + $id) -join ' ')) {
            throw 'El firmware no agrego la entrada al final del orden existente.'
        }
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
