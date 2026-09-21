BeforeAll {
    $script:stopScript = (Resolve-Path (Join-Path $PSScriptRoot '..\..\tools\Stop-LiveStudioPort.ps1')).Path
    . $stopScript
    $script:workspace = 'C:\studio workspace'
    function New-ServerInfo {
        param([string] $Command, [int] $ProcessId = 41001, [int] $Created = 1)
        [pscustomobject]@{ CommandLine = $Command; ProcessId = $ProcessId; CreationDate = $Created }
    }
    $script:pythonCommand = '"C:\studio workspace\.intent-to-impact\studio\.venv\Scripts\python.exe" -B -m studio.serve'
    $script:viteCommand = '"node" "C:\studio workspace\apps\experience\node_modules\.bin\\..\vite\bin\vite.js" --host 127.0.0.1 --port 5173 --strictPort'
}

Describe 'Workspace server recognition' {
    It 'recognizes this workspace studio and the normalized Vite entry point' {
        Test-LiveStudioProcess (New-ServerInfo $pythonCommand) $workspace | Should -BeTrue
        Test-LiveStudioProcess (New-ServerInfo $viteCommand) $workspace | Should -BeTrue
        Test-LiveStudioProcess (New-ServerInfo '"C:\Program Files\nodejs\node.exe" "C:\studio workspace\apps\experience\node_modules\vite\bin\vite.js" preview --port 5173') $workspace | Should -BeTrue
    }
    It 'does not recognize unrelated processes, similarly named roots or missing metadata' {
        foreach ($command in @(
            '"C:\another\.intent-to-impact\studio\.venv\Scripts\python.exe" -B -m studio.serve',
            '"C:\studio workspace\.intent-to-impact\studio\.venv\Scripts\python.exe" unrelated.py',
            '"node" "C:\studio workspace-other\apps\experience\node_modules\vite\bin\vite.js"',
            '"node" unrelated.js',
            '"python" -m studio.serve',
            ''
        )) {
            Test-LiveStudioProcess (New-ServerInfo $command) $workspace | Should -BeFalse
        }
    }
}

Describe 'Port replacement' {
    BeforeEach {
        $script:listenerReads = 0
        Mock Get-LiveStudioListener {
            $script:listenerReads++
            if ($script:listenerReads -eq 1) {
                [pscustomobject]@{ OwningProcess = 41001 }
                [pscustomobject]@{ OwningProcess = 41001 }
            }
        }
        Mock Get-CimInstance { New-ServerInfo $pythonCommand }
        Mock Stop-Process {}
        Mock Start-Sleep {}
    }
    It 'does nothing on an unused port' {
        Mock Get-LiveStudioListener {}
        Stop-LiveStudioPort -WorkspaceRoot $workspace | Should -Contain 'Port 5173 is already available; no listening server to stop.'
        Should -Invoke Stop-Process -Times 0
        Should -Invoke Get-CimInstance -Times 0
    }

    It 'stops only the verified PID once and waits for port release' {
        Stop-LiveStudioPort -WorkspaceRoot $workspace | Should -Contain 'Port 5173 is available.'
        Should -Invoke Stop-Process -Times 1 -ParameterFilter { $Id -eq 41001 -and $Force }
        Should -Invoke Get-CimInstance -Times 2 -ParameterFilter { $Filter -eq 'ProcessId = 41001' }
    }
    It 'stops a recognized Vite server before replacement' {
        Mock Get-CimInstance { New-ServerInfo $viteCommand }
        Stop-LiveStudioPort -WorkspaceRoot $workspace
        Should -Invoke Stop-Process -Times 1 -ParameterFilter { $Id -eq 41001 }
    }
    It 'checks all owners before stopping any process' {
        Mock Get-LiveStudioListener {
            [pscustomobject]@{ OwningProcess = 41001 }
            [pscustomobject]@{ OwningProcess = 41002 }
        }
        Mock Get-CimInstance {
            if ($Filter -eq 'ProcessId = 41002') { New-ServerInfo '"node" unrelated.js' 41002 }
            else { New-ServerInfo $pythonCommand }
        }
        { Stop-LiveStudioPort -WorkspaceRoot $workspace } | Should -Throw '*unrelated*41002*'
        Should -Invoke Stop-Process -Times 0
    }
    It 'does not stop a PID reused by a different process' {
        $script:processReads = 0
        Mock Get-CimInstance {
            $script:processReads++
            New-ServerInfo $pythonCommand 41001 $script:processReads
        }
        { Stop-LiveStudioPort -WorkspaceRoot $workspace } | Should -Throw '*changed*'
        Should -Invoke Stop-Process -Times 0
    }
    It 'surfaces process termination errors without claiming a free port' {
        Mock Stop-Process { throw 'Access denied' }
        { Stop-LiveStudioPort -WorkspaceRoot $workspace } | Should -Throw '*Access denied*'
    }
    It 'fails instead of starting when the port is still occupied' {
        Mock Get-LiveStudioListener { [pscustomobject]@{ OwningProcess = 41001 } }
        { Stop-LiveStudioPort -WorkspaceRoot $workspace -TimeoutSeconds 1 } | Should -Throw '*not released*'
        Should -Invoke Stop-Process -Times 1
    }
    It 'tolerates a server exiting before process inspection' {
        Mock Get-CimInstance { $null }
        Stop-LiveStudioPort -WorkspaceRoot $workspace | Should -Contain 'Port 5173 is available.'
        Should -Invoke Stop-Process -Times 0
    }
}

Describe 'Listener query failures' {
    It 'does not hide permission or system errors as an unused port' {
        Mock Get-NetTCPConnection { throw 'Cannot inspect network state' }
        { Get-LiveStudioListener } | Should -Throw '*Cannot inspect network state*'
    }

    Describe 'Direct script invocation' {
        BeforeEach {
            $script:networkReads = 0
            Mock Get-NetTCPConnection {
                $script:networkReads++
                if ($script:networkReads -eq 1) { [pscustomobject]@{ OwningProcess = 41001 } }
            }
            $script:repoRoot = Split-Path -Parent (Split-Path -Parent $stopScript)
            $script:repoCommand = '"' + (Join-Path $repoRoot '.intent-to-impact\studio\.venv\Scripts\python.exe') + '" -B -m studio.serve'
            Mock Get-CimInstance { New-ServerInfo $repoCommand }
            Mock Stop-Process {}
            Mock Start-Sleep {}
        }
        It 'executes cleanup directly with the workspace inferred from its own location' {
            Push-Location $TestDrive
            try {
                & $stopScript | Should -Contain 'Port 5173 is available.'
            } finally {
                Pop-Location
            }
            Should -Invoke Stop-Process -Times 1 -ParameterFilter { $Id -eq 41001 }
            Should -Invoke Get-NetTCPConnection -Times 2 -ParameterFilter { $LocalPort -eq 5173 -and $State -eq 'Listen' }
        }
        It 'accepts an explicit workspace when invoked directly' {
            Mock Get-CimInstance { New-ServerInfo $pythonCommand }
            & $stopScript -WorkspaceRoot $workspace -TimeoutSeconds 1 | Should -Contain 'Port 5173 is available.'
            Should -Invoke Stop-Process -Times 1 -ParameterFilter { $Id -eq 41001 }
        }
        It 'only imports definitions when dot-sourced, as used by the launcher' {
            . $stopScript
            Should -Invoke Get-NetTCPConnection -Times 0
            Should -Invoke Stop-Process -Times 0
            Get-Command Stop-LiveStudioPort | Should -Not -BeNullOrEmpty
        }
        It 'reports an already-free port when run directly' {
            Mock Get-NetTCPConnection {}
            & $stopScript | Should -Contain 'Port 5173 is already available; no listening server to stop.'
            Should -Invoke Stop-Process -Times 0
        }
        It 'still refuses unrelated listeners when run directly' {
            Mock Get-CimInstance { New-ServerInfo '"node" unrelated.js' }
            { & $stopScript } | Should -Throw '*unrelated or unidentifiable PID 41001*'
            Should -Invoke Stop-Process -Times 0
        }
    }
}
