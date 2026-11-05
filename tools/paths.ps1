# Relative source names for the Windows build, compatible with .NET Framework.
function ConvertTo-ProjectRelativePath {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$Path
    )
    $rootPrefix = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
    $absolutePath = [IO.Path]::GetFullPath($Path)
    if (-not $absolutePath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La fuente no pertenece al proyecto: $Path"
    }
    $absolutePath.Substring($rootPrefix.Length).Replace('\', '/')
}
