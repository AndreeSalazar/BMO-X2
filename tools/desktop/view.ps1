param(
    [Parameter(Mandatory)][string]$Renderer,
    [Parameter(Mandatory)][string]$Ready
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class HostCounters {
    [StructLayout(LayoutKind.Sequential)]
    public struct Memory {
        public uint Length, Load;
        public ulong Total, Available, TotalPage, AvailablePage, TotalVirtual, AvailableVirtual, ExtendedVirtual;
    }

    [DllImport("kernel32.dll")]
    public static extern bool GetSystemTimes(out long idle, out long kernel, out long user);
    [DllImport("kernel32.dll")]
    public static extern bool GlobalMemoryStatusEx(ref Memory memory);
}
'@
$width = 432
$height = 248
$accent = @('#5ad8ff', '#ad92ff', '#6ee7b7', '#ff7c98')
$workspaces = @('Inicio', 'Desarrollo', 'Medios', 'Sistema')
$format = [Drawing.Imaging.PixelFormat]::Format32bppRgb

$start = New-Object Diagnostics.ProcessStartInfo $Renderer
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardInput = $true
$start.RedirectStandardOutput = $true
$process = [Diagnostics.Process]::Start($start)
$stream = New-Object IO.BinaryReader $process.StandardOutput.BaseStream

$form = New-Object Windows.Forms.Form
$form.Text = 'BMO-X2 | Escritorio Rust (HOST)'
$form.StartPosition = 'CenterScreen'
$form.ClientSize = New-Object Drawing.Size (2 * $width), (2 * $height)
$form.FormBorderStyle = 'FixedSingle'
$form.MaximizeBox = $false
$form.KeyPreview = $true
$image = New-Object Windows.Forms.PictureBox
$image.Dock = 'Fill'
$image.SizeMode = 'StretchImage'
$form.Controls.Add($image)

function Add-Label($text, $x, $y, $color, $background, $size) {
    $label = New-Object Windows.Forms.Label
    $label.Text = $text
    $label.Location = New-Object Drawing.Point $x, $y
    $label.AutoSize = $true
    $label.ForeColor = [Drawing.ColorTranslator]::FromHtml($color)
    $label.BackColor = [Drawing.ColorTranslator]::FromHtml($background)
    $label.Font = New-Object Drawing.Font 'Segoe UI', $size
    $image.Controls.Add($label)
    $label
}

$brand = Add-Label 'BMO-X2' 22 7 '#e7efff' '#161722' 14
$status = Add-Label '' 752 12 '#e7efff' '#161722' 10
$resources = Add-Label 'HOST  CPU --  RAM --' 548 12 '#adb6cf' '#161722' 10
$resources.MaximumSize = New-Object Drawing.Size 199, 24
$title = Add-Label '' 96 157 '#edf1ff' '#222334' 12
$activity = Add-Label 'Actividad' 589 229 '#edf1ff' '#222334' 11
$badges = @(
    (Add-Label '1' 508 158 '#edf1ff' '#222334' 11),
    (Add-Label '2' 803 229 '#edf1ff' '#222334' 11)
)
foreach ($badge in $badges) { $badge.Visible = $false }
$null = Add-Label 'Ctrl+Alt+1-4  Espacios     Alt+1-9  Ventanas     BMO-X2 Ring 0  Sin enlace' 22 460 '#adb6cf' '#0d0e17' 11
$samples = @{ Idle = 0L; Total = 0L }

function Update-Resources {
    $idle = $kernel = $user = 0L
    $cpu = '--'
    if ([HostCounters]::GetSystemTimes([ref]$idle, [ref]$kernel, [ref]$user)) {
        $total = $kernel + $user
        if ($samples.Total -gt 0 -and $total -gt $samples.Total) {
            $busy = 100 * (1 - ($idle - $samples.Idle) / ($total - $samples.Total))
            $cpu = '{0:F0}%' -f [Math]::Max(0, [Math]::Min(100, $busy))
        }
        $samples.Idle = $idle
        $samples.Total = $total
    }
    $memory = New-Object HostCounters+Memory
    $memory.Length = [Runtime.InteropServices.Marshal]::SizeOf($memory)
    $ram = '--'
    if ([HostCounters]::GlobalMemoryStatusEx([ref]$memory)) { $ram = "$($memory.Load)%" }
    $text = "HOST   CPU $cpu   RAM $ram"
    if ($resources.Text -ne $text) { $resources.Text = $text }
}

$timer = New-Object Windows.Forms.Timer
$timer.Interval = 1000
$timer.Add_Tick({ Update-Resources })

function Show-Frame {
    $active = $stream.ReadByte()
    $focused = $stream.ReadByte()
    if ($active -notin 1..4) { throw 'Espacio invalido del compositor.' }
    $pixels = $stream.ReadBytes($width * $height * 4)
    if ($pixels.Length -ne $width * $height * 4) { throw 'Cuadro incompleto del compositor.' }
    $bitmap = New-Object Drawing.Bitmap $width, $height, $format
    $rect = New-Object Drawing.Rectangle 0, 0, $width, $height
    $bits = $bitmap.LockBits($rect, [Drawing.Imaging.ImageLockMode]::WriteOnly, $format)
    try { [Runtime.InteropServices.Marshal]::Copy($pixels, 0, $bits.Scan0, $pixels.Length) }
    finally { $bitmap.UnlockBits($bits) }
    $previous = $image.Image
    $image.Image = $bitmap
    if ($previous) { $previous.Dispose() }
    $status.Text = "Espacio $active / 4"
    $title.Text = $workspaces[$active - 1]
    $activeColor = [Drawing.ColorTranslator]::FromHtml($accent[$active - 1])
    $neutral = [Drawing.ColorTranslator]::FromHtml('#edf1ff')
    $brand.ForeColor = $activeColor
    $title.ForeColor = if ($focused -eq 1) { $activeColor } else { $neutral }
    $activity.ForeColor = if ($focused -eq 2) { $activeColor } else { $neutral }
    for ($index = 0; $index -lt $tabs.Count; $index++) {
        $color = if ($index + 1 -eq $active) { $accent[$index] } else { '#9ca6bd' }
        $tabs[$index].ForeColor = [Drawing.ColorTranslator]::FromHtml($color)
    }
}

function Send-Chord([int]$number, [int]$modifiers) {
    $process.StandardInput.WriteLine("$($number + 1) $modifiers")
    $process.StandardInput.Flush()
    Show-Frame
}

$tabs = @(foreach ($number in 1..4) {
    $tab = Add-Label "$number" (350 + ($number - 1) * 48) 6 '#9ca6bd' '#161722' 13
    $tab.Cursor = [Windows.Forms.Cursors]::Hand
    $tab.Add_Click({ param($sender, $eventArgs) Send-Chord ([int]$sender.Text) 34 })
    $tab
})
$form.Add_KeyDown({
    param($sender, $eventArgs)
    $number = $eventArgs.KeyValue - 48
    foreach ($badge in $badges) { $badge.Visible = $eventArgs.Alt -and -not $eventArgs.Control }
    if ($eventArgs.Alt -and $number -in 1..9) {
        $eventArgs.SuppressKeyPress = $true
        if (-not $eventArgs.Shift) {
            $modifiers = if ($eventArgs.Control) { 34 } else { 32 }
            Send-Chord $number $modifiers
        }
    }
})
$form.Add_KeyUp({
    param($sender, $eventArgs)
    foreach ($badge in $badges) { $badge.Visible = $eventArgs.Alt -and -not $eventArgs.Control }
})
$form.Add_Deactivate({ foreach ($badge in $badges) { $badge.Visible = $false } })
$form.Add_Shown({
    Update-Resources
    $timer.Start()
    $capture = New-Object Drawing.Bitmap $image.Width, $image.Height
    try {
        $image.DrawToBitmap($capture, $image.ClientRectangle)
        $capture.Save((Join-Path (Split-Path $Ready) 'preview.png'), [Drawing.Imaging.ImageFormat]::Png)
    }
    finally { $capture.Dispose() }
    Set-Content -LiteralPath $Ready -Value 'Ventana visible.' -Encoding ascii
})

try {
    Show-Frame
    [void]$form.ShowDialog()
}
finally {
    $timer.Dispose()
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(2000)) { $process.Kill() }
    $process.Dispose()
    $stream.Dispose()
    if ($image.Image) { $image.Image.Dispose() }
    $form.Dispose()
}
