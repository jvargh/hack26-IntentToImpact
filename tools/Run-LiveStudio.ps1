param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.intent-to-impact\studio\.venv\Scripts\python.exe'
$app = Join-Path $root 'apps\experience'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'The studio environment is missing. Follow apps\control-plane\studio\README.md to create it and install the pinned requirements.'
}
if (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 5173 is already occupied. Stop the preview or studio process you started before launching another; this script will not terminate other processes.'
}
Push-Location $app
try {
    if (-not $SkipBuild) {
        & npm run check:studio
        if ($LASTEXITCODE -ne 0) { throw 'Studio contract validation failed.' }
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed; the server was not started.' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $app 'dist\index.html'))) {
        throw 'Frontend assets are missing. Run this script without -SkipBuild.'
    }
} finally {
    Pop-Location
}

$oldPythonPath = $env:PYTHONPATH
Push-Location $root
try {
    $env:PYTHONPATH = Join-Path $root 'apps\control-plane'
    Write-Output 'Starting http://127.0.0.1:5173/ - local machine only.'
    Write-Output 'Generate sends consented input to the configured Foundry model and incurs inference charges.'
    Write-Output 'Package generation compiles local Bicep; it does not deploy to Azure.'
    & $python -B -m studio.serve
    if ($LASTEXITCODE -ne 0) { throw "Studio stopped with exit code $LASTEXITCODE." }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    Pop-Location
}
