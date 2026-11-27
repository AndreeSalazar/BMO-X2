[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BmoRoot,
    [Parameter(Mandatory=$true)][string]$Output,
    [string[]]$RustFlags = @()
)

$ErrorActionPreference = 'Stop'
$BmoRoot = (Resolve-Path -LiteralPath $BmoRoot).Path
$Output = (Resolve-Path -LiteralPath $Output).Path
$Flags = @('--edition=2021', '--crate-type=rlib') + $RustFlags
$Hash = Join-Path $Output 'libbmo_hash.rlib'
$Front = Join-Path $Output 'libbmo_spirv_front.rlib'
$Bsf = Join-Path $Output 'libbmo_bsf.rlib'

& rustc @Flags --crate-name bmo_hash (Join-Path $BmoRoot 'platform/shared/bmo-hash/src/lib.rs') -o $Hash
if ($LASTEXITCODE) { throw "BSF BLAKE3: $LASTEXITCODE" }
& rustc @Flags --crate-name bmo_spirv_front (Join-Path $BmoRoot 'toolchain/lang/spirv/src/lib.rs') -o $Front
if ($LASTEXITCODE) { throw "BSF frontend: $LASTEXITCODE" }
$Dependencies = @('--extern', "bmo_hash=$Hash", '--extern', "bmo_spirv_front=$Front")
& rustc @Flags @Dependencies --crate-name bmo_bsf (Join-Path $BmoRoot 'toolchain/lang/spirv/bsf/src/lib.rs') -o $Bsf
if ($LASTEXITCODE) { throw "BSF library: $LASTEXITCODE" }
$Bsf
