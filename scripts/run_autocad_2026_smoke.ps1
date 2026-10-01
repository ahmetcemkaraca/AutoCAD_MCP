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

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$evidenceDirectory = Join-Path $repositoryRoot "logs"
$evidenceName = "autocad-mcp-smoke-{0}-{1}.log" -f (Get-Date -Format "yyyyMMddTHHmmssZ"), ([guid]::NewGuid().ToString("N"))
$evidencePath = Join-Path $evidenceDirectory $evidenceName
$exitCode = 0

New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
New-Item -ItemType File -Path $evidencePath -ErrorAction Stop | Out-Null

function Write-Evidence([object]$Value) {
    $Value | Tee-Object -FilePath $evidencePath -Append
}

Push-Location -LiteralPath $repositoryRoot
try {
    $gitRevision = & git rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitRevision)) {
        throw "The smoke must run from a checked-out Git revision."
    }
    $gitRevision = $gitRevision.Trim()
    $gitBranch = & git branch --show-current
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitBranch)) {
        throw "The smoke must run from a named review branch."
    }
    $gitBranch = $gitBranch.Trim()
    & git diff --quiet --ignore-submodules --
    if ($LASTEXITCODE -ne 0) {
        throw "The tracked worktree has unstaged changes."
    }
    & git diff --cached --quiet --ignore-submodules --
    if ($LASTEXITCODE -ne 0) {
        throw "The tracked worktree has staged changes."
    }
    $lockPath = Join-Path $repositoryRoot "uv.lock"
    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
        throw "uv.lock is required for the smoke."
    }
    $lockGitBlob = & git rev-parse "HEAD:uv.lock"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($lockGitBlob)) {
        throw "The checked-out revision must contain uv.lock."
    }
    $lockGitBlob = $lockGitBlob.Trim()
    $windows = Get-CimInstance -ClassName Win32_OperatingSystem
    $sourceItem = Get-Item -LiteralPath $source
    $installationItem = Get-Item -LiteralPath $installation
    $preflightEvidence = [ordered]@{
        event = "runner-preflight"
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        windows = [ordered]@{
            caption = $windows.Caption
            version = $windows.Version
            build = $windows.BuildNumber
        }
        repository = [ordered]@{
            branch = $gitBranch
            head = $gitRevision
            tracked_worktree_clean = $true
            uv_lock_git_blob = $lockGitBlob
            uv_lock_sha256 = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
        }
        source = [ordered]@{
            path = $source
            sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
            size = $sourceItem.Length
            last_write_utc = $sourceItem.LastWriteTimeUtc.ToString("o")
        }
        installation = [ordered]@{
            path = $installation
            size = $installationItem.Length
            last_write_utc = $installationItem.LastWriteTimeUtc.ToString("o")
            product_name = $installationItem.VersionInfo.ProductName
            product_version = $installationItem.VersionInfo.ProductVersion
            file_version = $installationItem.VersionInfo.FileVersion
        }
    }
    Write-Evidence ("AUTOCAD_MCP_SMOKE_RUNNER_EVIDENCE=" + ($preflightEvidence | ConvertTo-Json -Compress))
    & uv --version 2>&1 | Tee-Object -FilePath $evidencePath -Append
    if ($LASTEXITCODE -ne 0) {
        $exitCode = $LASTEXITCODE
    }
    if ($exitCode -eq 0) {
        & uv sync --frozen --group dev 2>&1 | Tee-Object -FilePath $evidencePath -Append
        $exitCode = $LASTEXITCODE
    }
    if ($exitCode -eq 0) {
        $pythonEvidence = & uv run --frozen python -c "import json, struct, sys; details = {'implementation': sys.implementation.name, 'version': sys.version, 'bits': struct.calcsize('P') * 8}; assert sys.version_info[:2] == (3, 12) and details['bits'] == 64, details; print(json.dumps(details, sort_keys=True))" 2>&1
        $exitCode = $LASTEXITCODE
        $pythonEvidence | Tee-Object -FilePath $evidencePath -Append
    }
    if ($exitCode -eq 0) {
        & uv run --frozen pytest tests/windows/test_autocad_2026_smoke.py -m autocad --run-autocad --capture=tee-sys -vv --tb=short 2>&1 | Tee-Object -FilePath $evidencePath -Append
        $exitCode = $LASTEXITCODE
    }
} catch {
    $exitCode = 1
    try {
        Write-Evidence ("AUTOCAD_MCP_SMOKE_RUNNER_ERROR=" + $_.Exception.GetType().Name)
    } catch {
        [Console]::Error.WriteLine("AutoCAD MCP smoke evidence could not be written.")
    }
} finally {
    try {
        try {
            if (Test-Path -LiteralPath $source) {
                $postflightEvidence = [ordered]@{
                    event = "runner-postflight"
                    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
                    source = [ordered]@{
                        path = $source
                        sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
                        size = (Get-Item -LiteralPath $source).Length
                        last_write_utc = (Get-Item -LiteralPath $source).LastWriteTimeUtc.ToString("o")
                    }
                    exit_code = $exitCode
                }
                Write-Evidence ("AUTOCAD_MCP_SMOKE_RUNNER_EVIDENCE=" + ($postflightEvidence | ConvertTo-Json -Compress))
            }
        } catch {
            if ($exitCode -eq 0) {
                $exitCode = 1
            }
            try {
                Write-Evidence ("AUTOCAD_MCP_SMOKE_POSTFLIGHT_ERROR=" + $_.Exception.GetType().Name)
            } catch {
                [Console]::Error.WriteLine("AutoCAD MCP smoke postflight evidence could not be written.")
            }
        }
    } finally {
        Pop-Location
    }
}
Write-Output "Local evidence log: $evidencePath"
exit $exitCode
