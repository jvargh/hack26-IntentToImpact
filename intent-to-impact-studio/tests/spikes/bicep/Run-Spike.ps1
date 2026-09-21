#requires -Version 7.2
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$ownedRoot = Join-Path $workspace '.intent-to-impact\spikes\SPK-04-01'

foreach ($relative in @('.intent-to-impact', '.intent-to-impact\spikes', '.intent-to-impact\spikes\SPK-04-01')) {
    $path = Join-Path $workspace $relative
    if ((Test-Path -LiteralPath $path) -and
        ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing reparse point in owned evidence path: $relative"
    }
}

$runId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$runDirectory = Join-Path $ownedRoot $runId
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$env:SPK_BICEP_POWERSHELL_VERSION = $PSVersionTable.PSVersion.ToString()
& python -B (Join-Path $PSScriptRoot 'run_spike.py') --run-directory $runDirectory
$result = $LASTEXITCODE
if ($result -ne 0) {
    throw "SPK-04-01 failed or blocked (exit $result). Evidence: $runDirectory"
}
