[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDwg,

    [Parameter(Mandatory = $true)]
    [string]$AutoCADInstallationPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RequiredAbsolutePath([string]$Value, [string]$Label) {
    if ($Value -notmatch '^(?:[A-Za-z]:\\|\\\\)') {
        throw "$Label must be an absolute path."
    }
    $item = Get-Item -LiteralPath $Value
    if ($item.PSIsContainer) {
        throw "$Label must be a file."
    }
    return $item.FullName
}

$source = Get-RequiredAbsolutePath $SourceDwg "SourceDwg"
$installation = Get-RequiredAbsolutePath $AutoCADInstallationPath "AutoCADInstallationPath"
if ([IO.Path]::GetExtension($source).ToLowerInvariant() -ne ".dwg") {
    throw "SourceDwg must name a .dwg file."
}
if ((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReadOnly) {
    # The required immutable source is acceptable.
} else {
    throw "SourceDwg must be immutable (read-only)."
}
if ([IO.Path]::GetFileName($installation).ToLowerInvariant() -ne "acad.exe") {
    throw "AutoCADInstallationPath must name acad.exe."
}

$env:AUTOCAD_MCP_SMOKE_SOURCE_DWG = $source
$env:AUTOCAD_MCP_AUTOCAD_INSTALLATION = $installation
$env:AUTOCAD_MCP_SMOKE_RELEASE = "2026"
$env:AUTOCAD_MCP_SMOKE_DISPOSABLE = "YES"

& uv sync --frozen --group dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& uv run pytest tests/windows/test_autocad_2026_smoke.py -m autocad --run-autocad -vv --tb=short
exit $LASTEXITCODE
