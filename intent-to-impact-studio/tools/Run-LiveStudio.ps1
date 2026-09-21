param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $workspaceRoot
$python = Join-Path $repositoryRoot '.intent-to-impact\studio\.venv\Scripts\python.exe'
$app = Join-Path $workspaceRoot 'apps\experience'
. (Join-Path $PSScriptRoot 'Stop-LiveStudioPort.ps1')

if (-not (Test-Path -LiteralPath $python)) {
    throw 'The studio environment is missing. Follow intent-to-impact-studio\apps\control-plane\studio\README.md to create it and install the pinned requirements.'
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

Stop-LiveStudioPort -WorkspaceRoot $workspaceRoot

$oldPythonPath = $env:PYTHONPATH
Push-Location $workspaceRoot
try {
    $env:PYTHONPATH = Join-Path $workspaceRoot 'apps\control-plane'
    Write-Output 'Starting http://127.0.0.1:5173/ - local machine only.'
    Write-Output 'Generate sends consented input to the configured Foundry model and incurs inference charges.'
    Write-Output 'Package generation compiles local Bicep; it does not deploy to Azure.'
    & $python -B -m studio.serve
    if ($LASTEXITCODE -ne 0) { throw "Studio stopped with exit code $LASTEXITCODE." }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    Pop-Location
}
