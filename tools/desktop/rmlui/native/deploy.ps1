[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Run,[ValidateSet('A:\')][string]$Volume='A:\')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$runPath=(Get-Item -LiteralPath $Run).FullName
if ((Split-Path $runPath -Parent) -ne (Join-Path $root 'build/CASM')) { throw 'Run fuera de build/CASM.' }
if ((Get-Content -LiteralPath (Join-Path $runPath 'profile.txt') -Raw).Trim() -ne 'rmlui-desktop-media') { throw 'Perfil de arranque incompatible.' }
$media=Join-Path $runPath 'media'
$proof=Get-Content -LiteralPath (Join-Path $media 'manifest.json') -Raw | ConvertFrom-Json
if($proof.qemu_only -or $proof.usb_profile -or (Test-Path -LiteralPath (Join-Path $runPath 'native-usb.txt'))){throw 'El perfil USB QEMU no se instala en METAL.'}
$normal=$proof.Cases | Where-Object { $_.Case -eq 'normal' } | Select-Object -First 1
if ($proof.Passed -ne 2 -or $proof.Total -ne 2 -or -not $proof.disk_sbef -or
    -not $normal.DirectorRust -or -not $normal.SuperQVerified -or -not $normal.BootLogFat32Verified) {
    throw 'Faltan las pruebas QEMU de escritorio y lectura FAT32.'
}
$drive=[IO.DriveInfo]::new($Volume)
if (-not $drive.IsReady -or $drive.DriveFormat -ne 'FAT32') { throw 'A: debe ser un FAT32 existente y disponible.' }
$names=@('BMO-X2/DESKTOP/INICIO.X86','BMO-X2/DESKTOP/DESKTOP.SBF','EFI/BMO-X2/DESKTOP.EFI')
if (@($proof.files.PSObject.Properties).Count -ne $names.Count) { throw 'Manifiesto de archivos inesperado.' }
foreach($name in $names) {
    $source=Get-Item -LiteralPath (Join-Path $media $name)
    if (($source.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $proof.files.$name) {
        throw "Fuente modificada: $name"
    }
}
$legacy=@{}
foreach($name in @('EFI/BMO-X2/BMO-X2.EFI','BMO-X2/INICIO.X86','BMO-X2/DESKTOP.SBF','BMO-X2/BOOTLOG.TXT')) {
    $path=Join-Path $Volume $name
    if(Test-Path -LiteralPath $path -PathType Leaf){$legacy[$name]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
}
$written=@{}
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
    BootFile='\EFI\BMO-X2\DESKTOP.EFI';ReportFile='\BMO-X2\DESKTOP\BOOTLOG.TXT';
    Note='USB HID fisico sigue pendiente; no cambia NVRAM ni archivos ajenos al candidato.'}
$json=$record | ConvertTo-Json -Depth 8
Set-Content -LiteralPath (Join-Path $Volume 'BMO-X2/DESKTOP/DEPLOY.JSON') -Value $json -Encoding UTF8
Set-Content -LiteralPath (Join-Path $runPath 'fat32-deploy.json') -Value $json -Encoding UTF8
Write-Output 'Candidato copiado y verificado. Archivos ajenos al candidato conservados.'
Write-Output 'UEFI Boot from file: \EFI\BMO-X2\DESKTOP.EFI'
Write-Output 'Reporte de la prueba fisica: A:\BMO-X2\DESKTOP\BOOTLOG.TXT'
