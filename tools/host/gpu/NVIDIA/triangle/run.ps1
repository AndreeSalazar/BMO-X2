param(
    [string]$Sdk = $env:VULKAN_SDK,
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
if (-not $Sdk) { throw 'Indica el Vulkan SDK con -Sdk o VULKAN_SDK.' }
$Sdk = (Resolve-Path -LiteralPath $Sdk).Path
$Cl = (Get-Command cl.exe -CommandType Application).Source
$GLSLC = Join-Path $Sdk 'Bin/glslc.exe'
$Build = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../../build/gpu/NVIDIA/triangle-host'))
New-Item -Path $Build -ItemType Directory -Force | Out-Null

$Vertex = Join-Path $Build 'triangle.vert.spv'
$Fragment = Join-Path $Build 'triangle.frag.spv'
$RawVertex = Join-Path $Build 'triangle.vert.raw.spv'
$RawFragment = Join-Path $Build 'triangle.frag.raw.spv'
& $GLSLC --target-env=vulkan1.3 (Join-Path $PSScriptRoot 'triangle.vert') -o $RawVertex
if ($LASTEXITCODE) { throw "glslc vertex: $LASTEXITCODE" }
& $GLSLC --target-env=vulkan1.3 (Join-Path $PSScriptRoot 'triangle.frag') -o $RawFragment
if ($LASTEXITCODE) { throw "glslc fragment: $LASTEXITCODE" }

$Profile = Join-Path $PSScriptRoot '../../spirv_profile.py'
$VertexReport = & $Python -B $Profile --sdk $Sdk vertex $RawVertex $Vertex
if ($LASTEXITCODE) { throw "VERRANO vertex: $LASTEXITCODE" }
$FragmentReport = & $Python -B $Profile --sdk $Sdk fragment $RawFragment $Fragment
if ($LASTEXITCODE) { throw "VERRANO fragment: $LASTEXITCODE" }
@(($VertexReport | ConvertFrom-Json), ($FragmentReport | ConvertFrom-Json)) |
    ConvertTo-Json | Set-Content -Path (Join-Path $Build 'spirv-profile.json') -Encoding utf8

$Include = Join-Path $Sdk 'Include'
$Lib = Join-Path $Sdk 'Lib'
$Executable = Join-Path $Build 'triangle.exe'
& $Cl /nologo /std:c++17 /EHsc /O2 /W4 "/I$Include" "/Fo$Build\triangle.obj" "/Fe$Executable" `
    (Join-Path $PSScriptRoot 'triangle.cpp') /link "/LIBPATH:$Lib" vulkan-1.lib
if ($LASTEXITCODE) { throw "MSVC: $LASTEXITCODE" }

$PreviousLayerPath = $env:VK_LAYER_PATH
try {
    $env:VK_LAYER_PATH = Join-Path $Sdk 'Bin'
    & $Executable $Vertex $Fragment (Join-Path $Build 'frames') 2>&1 |
        Tee-Object -FilePath (Join-Path $Build 'renderer.txt')
    if ($LASTEXITCODE) { throw "Vulkan: $LASTEXITCODE" }
} finally {
    $env:VK_LAYER_PATH = $PreviousLayerPath
}

& $Python -B (Join-Path $PSScriptRoot 'export.py') $Build |
    Tee-Object -FilePath (Join-Path $Build 'preview.json')
if ($LASTEXITCODE) { throw "Exportacion: $LASTEXITCODE" }
