[CmdletBinding()]
param(
    [string] $WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateRange(1, 60)] [int] $TimeoutSeconds = 10
)

function Get-LiveStudioListener {
    try {
        Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction Stop
    } catch {
        if ($_.CategoryInfo.Category -ne 'ObjectNotFound') {
            throw
        }
    }
}

function Test-LiveStudioProcess {
    param(
        [Parameter(Mandatory)] $ProcessInfo,
        [Parameter(Mandatory)] [string] $WorkspaceRoot
    )

    if (-not $ProcessInfo.CommandLine) { return $false }
    $arguments = @([regex]::Matches($ProcessInfo.CommandLine, '"([^"]*)"|(\S+)') | ForEach-Object {
        if ($_.Groups[1].Success) { $_.Groups[1].Value } else { $_.Groups[2].Value }
    })
    if ($arguments.Count -lt 2) { return $false }
    $python = Join-Path $WorkspaceRoot '.intent-to-impact\studio\.venv\Scripts\python.exe'
    $vite = Join-Path $WorkspaceRoot 'apps\experience\node_modules\vite\bin\vite.js'

    # Windows venv listeners may run the base interpreter; match their actual
    # command-line entry point rather than the resolved executable location.
    if ([IO.Path]::IsPathFullyQualified($arguments[0]) -and
        [IO.Path]::GetFullPath($arguments[0]) -ieq [IO.Path]::GetFullPath($python)) {
        for ($index = 1; $index -lt $arguments.Count - 1; $index++) {
            if ($arguments[$index] -ceq '-m' -and $arguments[$index + 1] -ceq 'studio.serve') {
                return $true
            }
        }
    }
    if ([IO.Path]::GetFileName($arguments[0]) -in @('node', 'node.exe') -and
        [IO.Path]::IsPathFullyQualified($arguments[1])) {
        return [IO.Path]::GetFullPath($arguments[1]) -ieq [IO.Path]::GetFullPath($vite)
    }
    return $false
}

function Stop-LiveStudioPort {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $WorkspaceRoot,
        [ValidateRange(1, 60)] [int] $TimeoutSeconds = 10
    )

    $owners = @(Get-LiveStudioListener | Select-Object -ExpandProperty OwningProcess -Unique)
    if (-not $owners.Count) {
        Write-Output 'Port 5173 is already available; no listening server to stop.'
        return
    }
    $verified = @(
        foreach ($ownerId in $owners) {
            $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerId" -ErrorAction Stop
            if (-not $processInfo) { continue }
            if ($ownerId -eq $PID -or -not (Test-LiveStudioProcess -ProcessInfo $processInfo -WorkspaceRoot $WorkspaceRoot)) {
                throw "Port 5173 is owned by unrelated or unidentifiable PID $ownerId. Nothing was stopped. Inspect that process and stop it explicitly before starting the studio."
            }
            $processInfo
        }
    )
    foreach ($processInfo in $verified) {
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($processInfo.ProcessId)" -ErrorAction Stop
        if (-not $current) { continue }
        if ($current.CreationDate -ne $processInfo.CreationDate -or
            -not (Test-LiveStudioProcess -ProcessInfo $current -WorkspaceRoot $WorkspaceRoot)) {
            throw "PID $($processInfo.ProcessId) changed while preparing the restart. It was not stopped; run the launcher again after inspecting port 5173."
        }
        Write-Warning "Stopping this workspace's server on port 5173 (PID $($processInfo.ProcessId)). In-flight work may be interrupted; model completion may be unknown. Saved runs are preserved."
        Stop-Process -Id $processInfo.ProcessId -Force -ErrorAction Stop
    }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        if (-not @(Get-LiveStudioListener).Count) {
            Write-Output 'Port 5173 is available.'
            return
        }
        Start-Sleep -Milliseconds 100
    } while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds)
    throw "Port 5173 was not released within $TimeoutSeconds seconds. No new server was started."
}

# Importing functions for the launcher must not stop its server before building.
if ($MyInvocation.InvocationName -ne '.') {
    Stop-LiveStudioPort -WorkspaceRoot $WorkspaceRoot -TimeoutSeconds $TimeoutSeconds
}
