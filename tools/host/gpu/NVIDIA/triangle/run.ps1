param(
    [string]$Sdk = $env:VULKAN_SDK,
    [string]$Python = 'python',
    [switch]$Textured,
    [string]$BmoRoot
)

$ErrorActionPreference = 'Stop'
if (-not $Sdk) { throw 'Indica el Vulkan SDK con -Sdk o VULKAN_SDK.' }
$Sdk = (Resolve-Path -LiteralPath $Sdk).Path
$Cl = (Get-Command cl.exe -CommandType Application).Source
$GLSLC = Join-Path $Sdk 'Bin/glslc.exe'
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../..'))
$Bank = if ($Textured) { 'texture-host' } else { 'triangle-host' }
$Build = Join-Path $Root "build/gpu/NVIDIA/$Bank"
New-Item -Path $Build -ItemType Directory -Force | Out-Null

$Vertex = Join-Path $Build 'triangle.vert.spv'
$Fragment = Join-Path $Build 'triangle.frag.spv'
$RawVertex = Join-Path $Build 'triangle.vert.raw.spv'
$RawFragment = Join-Path $Build 'triangle.frag.raw.spv'
& $GLSLC --target-env=vulkan1.3 (Join-Path $PSScriptRoot 'triangle.vert') -o $RawVertex
if ($LASTEXITCODE) { throw "glslc vertex: $LASTEXITCODE" }
$FragmentSource = if ($Textured) { 'texture.frag' } else { 'triangle.frag' }
& $GLSLC --target-env=vulkan1.3 (Join-Path $PSScriptRoot $FragmentSource) -o $RawFragment
if ($LASTEXITCODE) { throw "glslc fragment: $LASTEXITCODE" }

$Profile = Join-Path $PSScriptRoot '../../spirv_profile.py'
$VertexReport = & $Python -B $Profile --sdk $Sdk vertex $RawVertex $Vertex
if ($LASTEXITCODE) { throw "VERRANO vertex: $LASTEXITCODE" }
$FragmentStage = if ($Textured) { 'textured-fragment' } else { 'fragment' }
$FragmentReport = & $Python -B $Profile --sdk $Sdk $FragmentStage $RawFragment $Fragment
if ($LASTEXITCODE) { throw "VERRANO fragment: $LASTEXITCODE" }
@(($VertexReport | ConvertFrom-Json), ($FragmentReport | ConvertFrom-Json)) |
    ConvertTo-Json | Set-Content -Path (Join-Path $Build 'spirv-profile.json') -Encoding utf8

$RenderMode = @()
$ExportMode = @()
if ($Textured) {
    if (-not $BmoRoot) { $BmoRoot = Join-Path (Split-Path $Root) 'BMO' }
    $Bridge = Join-Path $Build 'bsf-bridge.exe'
    $Bsf = & (Join-Path $PSScriptRoot '../../build-bsf.ps1') -BmoRoot $BmoRoot -Output $Build
    & rustc --edition=2021 -L "dependency=$Build" --extern "bmo_bsf=$Bsf" (Join-Path $PSScriptRoot '../../bsf_bridge.rs') -o $Bridge
    if ($LASTEXITCODE) { throw "BSF bridge: $LASTEXITCODE" }
    $Package = Join-Path $Build 'triangle.bsf'
    & $Bridge pack $Package $Vertex $Fragment
    if ($LASTEXITCODE) { throw "BSF pack: $LASTEXITCODE" }
    $Vertex = Join-Path $Build 'vertex.from-bsf.spv'
    $Fragment = Join-Path $Build 'fragment.from-bsf.spv'
    & $Bridge unpack $Package $Vertex $Fragment
    if ($LASTEXITCODE) { throw "BSF unpack: $LASTEXITCODE" }
    $Sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $VertexHash = [BitConverter]::ToString($Sha256.ComputeHash([IO.File]::ReadAllBytes($Vertex))).Replace('-', '')
        $FragmentHash = [BitConverter]::ToString($Sha256.ComputeHash([IO.File]::ReadAllBytes($Fragment))).Replace('-', '')
        if ($VertexHash -ne ($VertexReport | ConvertFrom-Json).sha256 -or
            $FragmentHash -ne ($FragmentReport | ConvertFrom-Json).sha256) {
            throw 'BSF: los shaders recuperados difieren del resultado validado por HOST.'
        }
    } finally {
        $Sha256.Dispose()
    }
    $RenderMode = @('textured')
    $ExportMode = @('--textured')
}

$Include = Join-Path $Sdk 'Include'
$Lib = Join-Path $Sdk 'Lib'
$Executable = Join-Path $Build 'triangle.exe'
& $Cl /nologo /std:c++17 /EHsc /O2 /W4 "/I$Include" "/Fo$Build\triangle.obj" "/Fe$Executable" `
    (Join-Path $PSScriptRoot 'triangle.cpp') /link "/LIBPATH:$Lib" vulkan-1.lib
if ($LASTEXITCODE) { throw "MSVC: $LASTEXITCODE" }

$PreviousLayerPath = $env:VK_LAYER_PATH
try {
    $env:VK_LAYER_PATH = Join-Path $Sdk 'Bin'
    & $Executable $Vertex $Fragment (Join-Path $Build 'frames') @RenderMode 2>&1 |
        Tee-Object -FilePath (Join-Path $Build 'renderer.txt')
    if ($LASTEXITCODE) { throw "Vulkan: $LASTEXITCODE" }
} finally {
    $env:VK_LAYER_PATH = $PreviousLayerPath
}

$Preview = & $Python -B (Join-Path $PSScriptRoot 'export.py') $Build @ExportMode
if ($LASTEXITCODE) { throw "Exportacion: $LASTEXITCODE" }
$Preview |
    Tee-Object -FilePath (Join-Path $Build 'preview.json')
