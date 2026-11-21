[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Run,[ValidateSet('A:\')][string]$Volume='A:\',[switch]$ExperimentalUsb,[switch]$Check,[switch]$NvidiaProbe)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$runPath=(Get-Item -LiteralPath $Run).FullName
if ((Split-Path $runPath -Parent) -ne (Join-Path $root 'build/CASM')) { throw 'Run fuera de build/CASM.' }
if ((Get-Content -LiteralPath (Join-Path $runPath 'profile.txt') -Raw).Trim() -ne 'rmlui-desktop-media') { throw 'Perfil de arranque incompatible.' }
if ((Test-Path -LiteralPath (Join-Path $runPath 'storage-quiesce.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-nvme.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-gsp-dma.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-guest-nvme.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-guest-ahci.txt'))) {
    throw 'El laboratorio AHCI/NVMe es exclusivo de QEMU.'
}
$media=Join-Path $runPath 'media'
$proof=Get-Content -LiteralPath (Join-Path $media 'manifest.json') -Raw | ConvertFrom-Json
if ($proof.amdvi_coexist -or $proof.amdvi_guest_dma -or $proof.amdvi_storage -or $proof.amdvi_routed -or $proof.amdvi_nvme -or $proof.amdvi_gsp_dma -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-coexist-probe.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-guest-dma.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-storage.txt')) -or
    (Test-Path -LiteralPath (Join-Path $runPath 'amdvi-routed.txt'))) {
    throw 'Los ensayos AMD-Vi con solicitantes virtuales son exclusivos de QEMU.'
}
$normal=$proof.Cases | Where-Object { $_.Case -eq 'normal' } | Select-Object -First 1
$gpuRun=Test-Path -LiteralPath (Join-Path $runPath 'nvidia-pci-probe.txt') -PathType Leaf
if ($gpuRun -ne [bool]$NvidiaProbe -or $gpuRun -ne [bool]$proof.nvidia_pci_probe -or
    ($gpuRun -and -not $normal.NvidiaPciProbeVerified)) {
    throw 'El ensayo GPU requiere -NvidiaProbe y su propia prueba PCI en QEMU.'
}
$amdviRun=Test-Path -LiteralPath (Join-Path $runPath 'amdvi-efi-probe.txt') -PathType Leaf
$amdviPost=Test-Path -LiteralPath (Join-Path $runPath 'amdvi-post-probe.txt') -PathType Leaf
$dmaCensus=Test-Path -LiteralPath (Join-Path $runPath 'dma-census-probe.txt') -PathType Leaf
$storageState=Test-Path -LiteralPath (Join-Path $runPath 'storage-state.txt') -PathType Leaf
$fullHd=Test-Path -LiteralPath (Join-Path $runPath 'full-hd.txt') -PathType Leaf
$fullHdNative=$fullHd -and (Get-Content -LiteralPath (Join-Path $runPath 'full-hd.txt') -Raw).Trim() -eq 'cpu-gop-native-1920x1080'
$gspSample=Test-Path -LiteralPath (Join-Path $runPath 'nvidia-gsp-sample.txt') -PathType Leaf
$gspStage=Test-Path -LiteralPath (Join-Path $runPath 'nvidia-gsp-stage.json') -PathType Leaf
$wprSample=$gspSample -and ((Get-Content -LiteralPath (Join-Path $runPath 'nvidia-gsp-sample.txt') -Raw).Trim() -eq 'ga106-gsp-wpr-read-only')
if ($wprSample -ne [bool]$proof.nvidia_wpr_sample -or
    ($wprSample -and @($proof.Cases | Where-Object { -not $_.GpuWprSampleSkipped }).Count)) {
    throw 'Falta la prueba de exclusion WPR para dispositivos que no son GA106.'
}
if ($gspSample -ne [bool]$proof.nvidia_gsp_sample -or ($gspSample -and
    (-not $gpuRun -or -not $fullHdNative -or @($proof.Cases | Where-Object { -not $_.GpuGspSampleSkipped }).Count))) {
    throw 'La muestra GSP requiere el perfil NVIDIA Full HD y las exclusiones verificadas en QEMU.'
}
if ($gspStage -ne [bool]$proof.nvidia_gsp_stage -or ($gspStage -and (-not $gspSample -or
    -not $normal.GspResidentVerified -or (($proof.Cases.GspStageStatus -join ',') -ne '5,4,1')))) {
    throw 'El GSP.BIN requiere la lectura completa y los rechazos verificados en QEMU.'
}
if ($amdviRun -ne [bool]$proof.amdvi_efi_probe) {
    throw 'La sonda AMD-Vi requiere su manifiesto.'
}
if ($amdviPost -ne [bool]$proof.amdvi_post_probe -or ($amdviPost -and -not $amdviRun)) {
    throw 'La captura post-EBS requiere el perfil AMD-Vi y su manifiesto.'
}
if ($dmaCensus -ne [bool]$proof.dma_census -or ($dmaCensus -and -not $amdviPost)) {
    throw 'El inventario DMA requiere el perfil post-EBS y su manifiesto.'
}
if ($storageState -ne [bool]$proof.storage_state -or ($storageState -and -not $dmaCensus)) {
    throw 'El informe de almacenamiento requiere el inventario DMA y su manifiesto.'
}
if ($fullHd -ne [bool]$proof.full_hd -or ($fullHd -and -not $storageState)) {
    throw 'El escritorio Full HD requiere su perfil y su manifiesto.'
}
if ($fullHdNative -ne [bool]$proof.full_hd_native -or ($fullHdNative -and -not $normal.FullHdNativeRasterVerified)) {
    throw 'Falta comprobar el raster directo a 1920x1080.'
}
if ($amdviPost) {
    $missing=$proof.Cases | Where-Object { $_.Case -eq 'amdvi-missing' } | Select-Object -First 1
    if (-not $normal.AmdViPostVerified -or $normal.AmdViPostPages -ne 2 -or
        -not $missing.AmdViPostVerified -or $missing.AmdViPostPages -ne 0) {
        throw 'Falta comprobar la ventana AMD-Vi posterior a ExitBootServices.'
    }
    if ($dmaCensus -and (-not $normal.DmaCensusVerified -or -not $missing.DmaCensusVerified -or
        -not $normal.DmaCensusPanelVerified)) {
        throw 'Falta comprobar el inventario DMA PCI y su panel de Ring 3.'
    }
    if ($storageState -and (-not $normal.StorageStateVerified -or -not $missing.StorageStateVerified -or
        -not $normal.StoragePanelVerified)) {
        throw 'Falta comprobar el estado AHCI/NVMe posterior al traspaso y el panel F3.'
    }
    if ($fullHd -and (-not $normal.FullHdGopVerified -or $normal.PresentedPixelsVerified -ne 2073600 -or
        -not $missing.FullHdFallbackVerified)) {
        throw 'Falta comprobar la salida 1920x1080 y el retorno al perfil base.'
    }
}
if ($amdviRun) {
    $rejected=$proof.Cases | Where-Object { $_.Case -eq 'external-permissions' } | Select-Object -First 1
    if (-not $normal.AmdViFirmwareVerified -or -not $normal.AmdViPresent -or
        -not $rejected.AmdViFirmwareVerified -or $rejected.AmdViPresent) {
        throw 'Falta corroborar el informe AMD-Vi con y sin IVRS en QEMU.'
    }
    if ($proof.amdvi_mmio_probe -and (-not $normal.AmdViMmioVerified -or -not $rejected.AmdViMmioVerified)) {
        throw 'Falta cotejar el estado MMIO de AMD-Vi en QEMU.'
    }
}
if($proof.qemu_only -or $proof.usb_profile -or (Test-Path -LiteralPath (Join-Path $runPath 'native-usb.txt'))) {
    if(-not $ExperimentalUsb -or $proof.usb_profile -ne 'both' -or $proof.usb_empty_ports -or
        $proof.hardware_profile -ne 'amd149c-usb2-root-experimental' -or
        -not $normal.UsbBothDevicesVerified -or -not $normal.UsbStopVerified -or
        -not $normal.UsbBusMasterRevoked -or -not $normal.UsbMmioRevoked -or
        -not $normal.UsbMmioSupervisorNxVerified -or -not $normal.UsbPs2FallbackDisabled -or
        $normal.UsbDmaReservedBytes -ne 57344 -or $normal.UsbCodePages -ne 2) {
        throw 'El perfil USB QEMU no se instala en METAL. El candidato AMD requiere perfil conjunto y pruebas adicionales explicitas.'
    }
}
$caseCount=if($amdviPost){3}else{2}
if ($proof.Passed -ne $caseCount -or $proof.Total -ne $caseCount -or -not $proof.disk_sbef -or
    -not $normal.DirectorRust -or -not $normal.SuperQVerified -or -not $normal.BootLogFat32Verified) {
    throw 'Faltan las pruebas QEMU de escritorio y lectura FAT32.'
}
$drive=[IO.DriveInfo]::new($Volume)
if (-not $drive.IsReady -or $drive.DriveFormat -ne 'FAT32') { throw 'A: debe ser un FAT32 existente y disponible.' }
$dataFolder=if($gpuRun){'BMO-X2/GPU'}else{'BMO-X2/DESKTOP'}
$bootFile=if($gpuRun){'EFI/BMO-X2/NVIDIA.EFI'}else{'EFI/BMO-X2/DESKTOP.EFI'}
$reportName=if($gpuRun){'GPULOG.TXT'}else{'BOOTLOG.TXT'}
$names=@("$dataFolder/INICIO.X86","$dataFolder/DESKTOP.SBF")
if ($gspStage) {
    $gspProof=Get-Content -LiteralPath (Join-Path $runPath 'nvidia-gsp-stage.json') -Raw | ConvertFrom-Json
    $gspName="$dataFolder/GSP.BIN"
    if ($gspProof.release -ne '615.78.08' -or $gspProof.sha256 -ne $proof.files.$gspName -or
        $gspProof.bytes -ne $normal.GspResidentBytes) {throw 'El manifiesto GSP difiere de la prueba UEFI.'}
    if ([bool]$gspProof.prepare -ne [bool]$proof.nvidia_gsp_prepare -or
        ($gspProof.prepare -and -not $normal.GspPreparedByRing0)) {
        throw 'Falta verificar la preparacion pos-EBS de Ring 0.'
    }
    if ($gspProof.detached_dma -and (-not $gspProof.prepare -or -not $normal.GspDetachedDmaVerified -or
        -not $normal.GspStatusExportVerified -or -not $missing.GspStatusExportVerified)) {
        throw 'Falta comprobar las tablas DMA preparadas en RAM y el informe GSP.'
    }
    if ($gspProof.queues -and (-not $gspProof.detached_dma -or -not $normal.GspQueuePermissionsVerified -or
        $normal.GspQueuePagesVerified -ne 130)) {
        throw 'Falta comprobar la reserva y los permisos DMA de RMARGS y GspMem.'
    }
    if ($gspProof.libos -and (-not $gspProof.queues -or -not $normal.GspLibosVerified -or
        $normal.GspLibosPages -ne 99)) {
        throw 'Falta comprobar LIBOS y los ocho registros de arranque GSP.'
    }
    if ($gspProof.boot_chain -and (-not $gspProof.libos -or -not $normal.GspBootChainVerified -or
        $normal.GspBootChainPages -ne $gspProof.boot_chain.pages)) {
        throw 'Falta verificar los binarios firmados de arranque GSP y sus permisos DMA.'
    }
    if ($gspProof.wpr_page -and (-not $wprSample -or -not $normal.GspWprPageExcluded)) {
        throw 'Falta verificar que el perfil WPR excluye la VGA estandar.'
    }
    $names+=$gspName
}
$names+=$bootFile
if (@($proof.files.PSObject.Properties).Count -ne $names.Count) { throw 'Manifiesto de archivos inesperado.' }
foreach($name in $names) {
    $source=Get-Item -LiteralPath (Join-Path $media $name)
    if (($source.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $proof.files.$name) {
        throw "Fuente modificada: $name"
    }
}
if($Check){Write-Output "Preflight correcto: perfil, pruebas, FAT32 y $($names.Count) hashes verificados; sin escrituras.";return}
$legacy=@{}
foreach($name in @('EFI/BMO-X2/BMO-X2.EFI','BMO-X2/INICIO.X86','BMO-X2/DESKTOP.SBF','BMO-X2/BOOTLOG.TXT')) {
    $path=Join-Path $Volume $name
    if(Test-Path -LiteralPath $path -PathType Leaf){$legacy[$name]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
}
$written=@{}
$previous=@{}
$previousRunReceipt=Join-Path $runPath 'fat32-deploy.json'
if(Test-Path -LiteralPath $previousRunReceipt -PathType Leaf) {
    $saved=Get-Content -LiteralPath $previousRunReceipt -Raw | ConvertFrom-Json
    if($saved.Run -eq $proof.run -and $saved.PreviousFiles) {
        foreach($property in $saved.PreviousFiles.PSObject.Properties){$previous[$property.Name]=$property.Value}
    }
}
$previousReceipt=Join-Path $Volume "$dataFolder/DEPLOY.JSON"
if(Test-Path -LiteralPath $previousReceipt -PathType Leaf) {
    $receiptArchive=Join-Path $runPath 'fat32-backups/DEPLOY.before.json'
    if(-not (Test-Path -LiteralPath $receiptArchive)) {
        New-Item -ItemType Directory -Path (Split-Path $receiptArchive -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $previousReceipt -Destination $receiptArchive
    }
}
foreach($name in $names) {
    $target=[IO.Path]::GetFullPath((Join-Path $Volume $name))
    if(-not $target.StartsWith($Volume,[StringComparison]::OrdinalIgnoreCase)){throw 'Destino fuera de A:.'}
    if((Test-Path -LiteralPath $target -PathType Leaf) -and
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -eq $proof.files.$name) {
        $written[$name]=$proof.files.$name
        continue
    }
    $parent=Split-Path $target -Parent
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    if((Get-Item -LiteralPath $parent).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Destino con redireccion.'}
    $temp=$target+'.new-'+[guid]::NewGuid().ToString('N')
    Copy-Item -LiteralPath (Join-Path $media $name) -Destination $temp
    $hash=(Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant()
    if($hash -ne $proof.files.$name){throw 'Fallo la copia FAT32.'}
    if(Test-Path -LiteralPath $target) {
        $previousHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        $backup=Join-Path (Join-Path $runPath 'fat32-backups') ($name+'.'+$previousHash)
        New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup
        if((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash.ToLowerInvariant() -ne $previousHash){throw 'Respaldo del candidato no verificado.'}
        if(-not $previous.ContainsKey($name)){$previous[$name]=@{SHA256=$previousHash;Archive=$backup}}
    }
    Move-Item -LiteralPath $temp -Destination $target -Force
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash){throw 'Verificacion final FAT32 fallida.'}
    $written[$name]=$hash
}
foreach($name in $legacy.Keys){
    if((Get-FileHash -LiteralPath (Join-Path $Volume $name) -Algorithm SHA256).Hash -ne $legacy[$name]) {throw 'Cambio inesperado en el arranque anterior.'}
}
$record=[ordered]@{Schema=1;Evidence='HOST copy after QEMU FAT32 boot';Run=$proof.run;Volume=$Volume;FileSystem=$drive.DriveFormat;
    Files=$written;LegacyFilesUnchanged=$legacy;PhysicalBootVerified=$false;PhysicalUsbVerified=$false;
    PreviousFiles=$previous;ExperimentalUsb=[bool]$ExperimentalUsb;HardwareProfile=$proof.hardware_profile;AmdViFirmwareProbe=$amdviRun;
    AmdViMmioProbe=[bool]$proof.amdvi_mmio_probe;
    AmdViPostProbe=$amdviPost;
    DmaCensus=$dmaCensus;
    StorageState=$storageState;
    FullHd=$fullHd;
    FullHdNative=$fullHdNative;
    NvidiaGspSample=$gspSample;
    NvidiaWprProbe=$wprSample;
    NvidiaWprPreparation=($gspStage -and [bool]$gspProof.wpr_page);
    NvidiaGspStage=$gspStage;
    NvidiaGspPrepare=[bool]$proof.nvidia_gsp_prepare;
    NvidiaGspQueues=($gspStage -and [bool]$gspProof.queues);
    NvidiaGspLibos=($gspStage -and [bool]$gspProof.libos);
    PhysicalNvidiaGspResponseVerified=$false;
    BootFile=('\'+$bootFile.Replace('/','\'));ReportFile=('\'+$dataFolder.Replace('/','\')+'\'+$reportName);
    Note='USB HID fisico sigue pendiente; no cambia NVRAM ni archivos ajenos al candidato.'}
$json=$record | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $previousReceipt -Value $json -Encoding UTF8
Set-Content -LiteralPath (Join-Path $runPath 'fat32-deploy.json') -Value $json -Encoding UTF8
Write-Output 'Candidato copiado y verificado. Archivos ajenos al candidato conservados.'
Write-Output "UEFI Boot from file: $($record.BootFile)"
Write-Output "Reporte de la prueba fisica: A:$($record.ReportFile)"
