param(
    [Parameter(Mandatory)][string]$Renderer,
    [Parameter(Mandatory)][string]$Ready
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
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
$status = Add-Label '' 741 12 '#e7efff' '#161722' 10
$title = Add-Label '' 96 157 '#edf1ff' '#222334' 12
$null = Add-Label 'Actividad' 563 229 '#edf1ff' '#222334' 11
$null = Add-Label '1-4 o clic en el panel   Cambiar de espacio' 22 460 '#adb6cf' '#0d0e17' 11

function Show-Frame {
    $active = $stream.ReadByte()
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
    $brand.ForeColor = [Drawing.ColorTranslator]::FromHtml($accent[$active - 1])
    for ($index = 0; $index -lt $tabs.Count; $index++) {
        $color = if ($index + 1 -eq $active) { $accent[$index] } else { '#9ca6bd' }
        $tabs[$index].ForeColor = [Drawing.ColorTranslator]::FromHtml($color)
    }
}

function Switch-Workspace([int]$number) {
    $process.StandardInput.WriteLine("$($number + 1) 32")
    $process.StandardInput.Flush()
    Show-Frame
}

$tabs = @(foreach ($number in 1..4) {
    $tab = Add-Label "$number" (350 + ($number - 1) * 48) 6 '#9ca6bd' '#161722' 13
    $tab.Cursor = [Windows.Forms.Cursors]::Hand
    $tab.Add_Click({ param($sender, $eventArgs) Switch-Workspace ([int]$sender.Text) })
    $tab
})
$form.Add_KeyDown({
    param($sender, $eventArgs)
    $number = $eventArgs.KeyValue - 48
    if ($number -in 1..4) {
        $eventArgs.SuppressKeyPress = $true
        Switch-Workspace $number
    }
})
$form.Add_Shown({
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
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(2000)) { $process.Kill() }
    $process.Dispose()
    $stream.Dispose()
    if ($image.Image) { $image.Image.Dispose() }
    $form.Dispose()
}
