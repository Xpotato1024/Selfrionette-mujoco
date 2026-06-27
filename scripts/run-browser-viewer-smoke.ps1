[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [int]$PublisherPort = 8768,
    [int]$ViewerPort = 5176,
    [string]$Preset = "sweep_x",
    [int]$Steps = 6,
    [double]$IntervalS = 0.033,
    [int]$GracePeriodS = 90,
    [switch]$OpenBrowser,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$viewerRoot = Join-Path $repoRoot "apps/mujoco-viewer"

function Get-UrlHost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ($Value.Contains(":") -and -not $Value.StartsWith("[")) {
        return "[$Value]"
    }

    return $Value
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutMilliseconds = 500
    )

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $success = $async.AsyncWaitHandle.WaitOne($TimeoutMilliseconds, $false)
        if (-not $success) {
            $client.Close()
            return $false
        }

        $client.EndConnect($async)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            Write-Host "$Name is listening on $HostName`:$Port"
            return $true
        }

        Start-Sleep -Milliseconds 300
    }

    return $false
}

function Format-CommandLine {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    return ($Arguments | ForEach-Object {
        if ($_ -match '\s|["'']') {
            '"' + ($_ -replace '"', '\"') + '"'
        } else {
            $_
        }
    }) -join " "
}

function Start-ChildProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    Write-Host "$Name command:"
    Write-Host "  $FilePath $(Format-CommandLine -Arguments $Arguments)"

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -PassThru `
        -NoNewWindow

    if (-not $process) {
        throw "Failed to start $Name."
    }

    Write-Host "$Name pid: $($process.Id)"
    return $process
}

function Stop-ChildProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $false)]
        [System.Diagnostics.Process]$Process
    )

    if (-not $Process) {
        return
    }

    try {
        if (-not $Process.HasExited) {
            Write-Host "Stopping $Name pid: $($Process.Id)"
            $null = Start-Process `
                -FilePath "taskkill.exe" `
                -ArgumentList @("/PID", $Process.Id, "/T", "/F") `
                -Wait `
                -PassThru `
                -NoNewWindow
            $null = $Process.WaitForExit(5000)
        }
    } catch {
        Write-Warning "Cleanup warning for $($Name): $($_.Exception.Message)"
    }
}

function Wait-ForStartupHealth {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$PublisherProcess,
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$ViewerProcess,
        [Parameter(Mandatory = $true)]
        [int]$TimeoutS
    )

    $deadline = (Get-Date).AddSeconds($TimeoutS)
    while ((Get-Date) -lt $deadline) {
        if ($PublisherProcess.HasExited -or $ViewerProcess.HasExited) {
            return $false
        }

        Start-Sleep -Milliseconds 500
    }

    return $true
}

$publisherUrlHost = Get-UrlHost -Value $HostName
$viewerUrlHost = Get-UrlHost -Value $HostName
$websocketUrl = "ws://$publisherUrlHost`:$PublisherPort"
$viewerPath = "/apps/mujoco-viewer/"
$viewerUrl = "http://$viewerUrlHost`:$ViewerPort$viewerPath?websocketUrl=$websocketUrl"
$shouldOpenBrowser = $false
if ($NoBrowser) {
    $shouldOpenBrowser = $false
} elseif ($OpenBrowser) {
    $shouldOpenBrowser = $true
}

Write-Host "Repository root:"
Write-Host "  $repoRoot"
Write-Host "Viewer root:"
Write-Host "  $viewerRoot"
Write-Host "Viewer URL:"
Write-Host "  $viewerUrl"
Write-Host "WebSocket URL:"
Write-Host "  $websocketUrl"

$script:cancelRequested = $false
$cancelHandler = [System.ConsoleCancelEventHandler]{
    param($sender, $eventArgs)

    $script:cancelRequested = $true
    $eventArgs.Cancel = $true
}
[System.Console]::add_CancelKeyPress($cancelHandler)

$publisherProcess = $null
$viewerProcess = $null
$browserOpened = $false
$exitCode = 0
$startupWaitSeconds = [Math]::Max(5, [Math]::Min($GracePeriodS, 20))

try {
    $publisherArgs = @(
        "run"
        "python"
        "scripts/run_replay_mujoco_websocket_publisher.py"
        "--host"
        $HostName
        "--port"
        $PublisherPort
        "--steps"
        $Steps
        "--interval-s"
        $IntervalS
        "--grace-period-s"
        $GracePeriodS
        "--preset"
        $Preset
    )

    $viewerArgs = @(
        "/c"
        "npm"
        "run"
        "dev"
        "--"
        "--host"
        $HostName
        "--port"
        $ViewerPort
        "--strictPort"
    )

    $publisherProcess = Start-ChildProcess -Name "publisher" -FilePath "uv" -Arguments $publisherArgs -WorkingDirectory $repoRoot
    $viewerProcess = Start-ChildProcess -Name "viewer" -FilePath "cmd.exe" -Arguments $viewerArgs -WorkingDirectory $viewerRoot

    if (-not (Wait-TcpPort -Name "publisher" -HostName $HostName -Port $PublisherPort -TimeoutSeconds $startupWaitSeconds)) {
        throw "publisher port $PublisherPort did not become ready on $HostName."
    }

    if (-not (Wait-TcpPort -Name "viewer" -HostName $HostName -Port $ViewerPort -TimeoutSeconds $startupWaitSeconds)) {
        throw "viewer port $ViewerPort did not become ready on $HostName."
    }

    if ($shouldOpenBrowser) {
        Write-Host "Opening browser:"
        Write-Host "  $viewerUrl"
        Start-Process $viewerUrl | Out-Null
        $browserOpened = $true
    } else {
        Write-Host "Browser open: skipped"
    }

    Write-Host "Publisher and viewer are running."
    Write-Host "Press Ctrl+C to stop both processes."

    if ($NoBrowser) {
        Write-Host "NoBrowser smoke completed after readiness and cleanup checks."
        $exitCode = 0
    } else {
        while ($true) {
            if ($script:cancelRequested) {
                $exitCode = 130
                break
            }

            if ($publisherProcess.HasExited) {
                $publisherProcess.Refresh()
                $publisherExitCode = [int]$publisherProcess.ExitCode
                if ($publisherExitCode -eq 0) {
                    Write-Host "Publisher completed successfully."
                    $exitCode = 0
                } else {
                    Write-Host "Publisher exited with code $publisherExitCode."
                    $exitCode = $publisherExitCode
                }
                break
            }

            if ($viewerProcess.HasExited) {
                $viewerProcess.Refresh()
                $viewerExitCode = [int]$viewerProcess.ExitCode
                throw "viewer exited unexpectedly with code $viewerExitCode."
            }

            Start-Sleep -Milliseconds 500
        }
    }
} catch {
    if ($exitCode -eq 0) {
        $exitCode = 1
    }
    Write-Error $_.Exception.Message
} finally {
    Stop-ChildProcess -Name "viewer" -Process $viewerProcess
    Stop-ChildProcess -Name "publisher" -Process $publisherProcess
    [System.Console]::remove_CancelKeyPress($cancelHandler)

    if ($browserOpened) {
        Write-Host "Browser was opened by the launcher."
    }
}

exit $exitCode
