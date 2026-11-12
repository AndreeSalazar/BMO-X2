# Open a verified QEMU disk image in a visible window.
[CmdletBinding()]
param(
    [string]$Run,
    [string]$Qemu = (Join-Path $env:ProgramFiles 'qemu/qemu-system-x86_64.exe')
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$runs = (Resolve-Path (Join-Path $root 'build/CASM')).Path
if (-not $Run) {
    foreach ($candidate in (Get-ChildItem -LiteralPath $runs -Directory -Filter 'run-*' | Sort-Object Name -Descending)) {
        $profile = Join-Path $candidate.FullName 'profile.txt'
        $result = Join-Path $candidate.FullName 'qemu-results.json'
        if ((Test-Path -LiteralPath $profile -PathType Leaf) -and
            (Get-Content -LiteralPath $profile -Raw).Trim() -eq 'ring0-splash-hd-0.1' -and
            (Test-Path -LiteralPath $result -PathType Leaf)) {
            $report = Get-Content -LiteralPath $result -Raw | ConvertFrom-Json
            if ($report.Total -gt 0 -and $report.Passed -eq $report.Total) {
                $Run = $candidate.FullName
                break
            }
        }
    }
}
if (-not $Run) { throw 'Ejecuta primero bmo-x2.ps1 -Accion gato-hd o indica -Run.' }
$runDir = Get-Item -LiteralPath $Run
if (-not ($runDir -is [IO.DirectoryInfo]) -or $runDir.Parent.FullName -ne $runs -or
    $runDir.Name -notlike 'run-*' -or ($runDir.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Indica un run dentro de build/CASM.'
}
$report = Get-Content -LiteralPath (Join-Path $runDir.FullName 'qemu-results.json') -Raw | ConvertFrom-Json
$config = Get-Content -LiteralPath (Join-Path $runDir.FullName 'qemu-run.json') -Raw | ConvertFrom-Json
if ($report.run -ne $runDir.Name -or $report.Total -lt 1 -or $report.Passed -ne $report.Total -or
    $config.cpu -notin @('qemu64','Nehalem') -or $config.ram_mib -notin @(256,1024)) {
    throw 'El run requiere un resultado QEMU aprobado y una configuracion conocida.'
}
$build = Get-Item -LiteralPath (Join-Path $runDir.FullName 'build')
$disk = Get-Item -LiteralPath (Join-Path $build.FullName 'puente-normal.img')
if (-not ($build -is [IO.DirectoryInfo]) -or ($build.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    -not ($disk -is [IO.FileInfo]) -or ($disk.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Falta una imagen normal de QEMU en el run.'
}
$Qemu = (Resolve-Path -LiteralPath $Qemu).Path
$share = Join-Path (Split-Path $Qemu) 'share'
$code = (Resolve-Path -LiteralPath (Join-Path $share 'edk2-x86_64-code.fd')).Path
$template = (Resolve-Path -LiteralPath (Join-Path $share 'edk2-i386-vars.fd')).Path
if (($disk.FullName + $code + $build.FullName) -match ',') {
    throw 'Las rutas de disco y firmware para QEMU deben estar libres de comas.'
}
$preview = Join-Path $build.FullName ('preview-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $preview | Out-Null
$vars = Join-Path $preview 'vars.fd'
Copy-Item -LiteralPath $template -Destination $vars
$stdout = Join-Path $preview 'qemu-stdout.log'
$stderr = Join-Path $preview 'qemu-stderr.log'
$arguments = @(
    '-name', 'BMO-X2', '-machine', 'pc', '-accel', 'tcg', '-smp', '1',
    '-cpu', $config.cpu, '-m', "$($config.ram_mib)M",
    '-drive', ('"if=pflash,format=raw,unit=0,readonly=on,file={0}"' -f $code),
    '-drive', ('"if=pflash,format=raw,unit=1,file={0}"' -f $vars),
    '-drive', ('"file={0},format=raw,if=ide,snapshot=on"' -f $disk.FullName),
    '-vga', 'std', '-display', 'sdl', '-serial', 'none', '-monitor', 'none', '-no-reboot'
)
$process = Start-Process -FilePath $Qemu -ArgumentList $arguments -WindowStyle Normal -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
if ($process.WaitForExit(500)) {
    throw "QEMU cerro al abrir la ventana. $(Get-Content -LiteralPath $stderr -Raw)"
}
Write-Output "Ventana QEMU BMO-X2 abierta (PID $($process.Id)). Imagen: $($disk.FullName)"
