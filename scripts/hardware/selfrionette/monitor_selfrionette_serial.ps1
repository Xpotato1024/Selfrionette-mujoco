<#
.SYNOPSIS
  Monitor the Selfrionette serial protocol from PlatformIO or PowerShell.

.DESCRIPTION
  Opens a serial port and streams Selfrionette firmware output.
  Supports live key controls, optional calibration trigger, timed runs,
  and display filtering by message level.

  Message levels are ordered as:
    status < warn < vector

  Display filtering is applied separately for normal mode and paused mode.
  This makes it possible to hide noisy vector lines while keeping status
  messages visible, or to suppress both vectors and warns during pauses.

.PARAMETER Port
  Serial port name to open. Default: COM5.

.PARAMETER BaudRate
  Baud rate for the serial connection. Default: 115200.

.PARAMETER DurationSeconds
  Optional maximum runtime. Use 0 to run until quit is requested.

.PARAMETER SendText
  Optional text to write once after the port opens.

.PARAMETER Calibrate
  Sends the single-character calibration command 'c' after the port opens,
  then pauses vector display until calibration completes.

.PARAMETER DisplayLevel
  Highest message level to show during normal operation.
  Allowed values: status, warn, vector.

.PARAMETER PausedDisplayLevel
  Highest message level to show while paused.
  Allowed values: status, warn, vector.

.PARAMETER Help
  Prints script help and exits.

.EXAMPLE
  .\scripts\hardware\selfrionette\monitor_selfrionette_serial.ps1 -Port COM5
  Opens COM5 and streams vector lines only.

.EXAMPLE
  .\scripts\hardware\selfrionette\monitor_selfrionette_serial.ps1 -Port COM5 -DisplayLevel warn
  Shows status and warn lines, and also vector lines.

.EXAMPLE
  .\scripts\hardware\selfrionette\monitor_selfrionette_serial.ps1 -Port COM5 -Calibrate
  Sends 'c', waits for calibration completion, then resumes vector output.

.EXAMPLE
  .\scripts\hardware\selfrionette\monitor_selfrionette_serial.ps1 -Port COM5 -PausedDisplayLevel status
  Pauses vector output while still showing status lines.

.EXAMPLE
  .\scripts\hardware\selfrionette\monitor_selfrionette_serial.ps1 -Port COM5 -DurationSeconds 10
  Runs for 10 seconds and then exits.

.NOTES
  Interactive keys:
    p = pause output according to PausedDisplayLevel
    r = resume output according to DisplayLevel
    c = send calibration command
    q = quit
#>
param(
  [string]$Port = 'COM5',
  [int]$BaudRate = 115200,
  [int]$DurationSeconds = 0,
  [string]$SendText = '',
  [switch]$Calibrate,
  [switch]$Help,
  [ValidateSet('status', 'warn', 'vector')]
  [string]$DisplayLevel = 'vector',
  [ValidateSet('status', 'warn', 'vector')]
  [string]$PausedDisplayLevel = 'status'
)

$ErrorActionPreference = 'Stop'

if ($Help) {
  Get-Help -Detailed $PSCommandPath
  exit 0
}

function New-SerialPort {
  param(
    [string]$Name,
    [int]$Rate
  )

  $port = [System.IO.Ports.SerialPort]::new($Name, $Rate, 'None', 8, 'One')
  $port.ReadTimeout = 500
  $port.NewLine = "`n"
  $port.DtrEnable = $true
  $port.RtsEnable = $true
  return $port
}

function Get-LevelRank {
  param([string]$Level)

  switch ($Level) {
    'status' { return 0 }
    'warn' { return 1 }
    'vector' { return 2 }
    default { return 2 }
  }
}

function Get-LineLevel {
  param([string]$Line)

  if ($Line.StartsWith('status,')) {
    return 'status'
  }

  if ($Line.StartsWith('warn,')) {
    return 'warn'
  }

  if ($Line.StartsWith('vector,')) {
    return 'vector'
  }

  return 'status'
}

function Test-ShouldDisplayLine {
  param(
    [string]$Line,
    [string]$LevelLimit
  )

  $lineLevel = Get-LineLevel -Line $Line
  return (Get-LevelRank -Level $lineLevel) -le (Get-LevelRank -Level $LevelLimit)
}

Write-Host "Opening $Port at $BaudRate baud."
Write-Host "Keys: p=pause, r=resume, c=send calibration, q=quit."
Write-Host ("Display levels: normal<={0}, paused<={1}" -f $DisplayLevel, $PausedDisplayLevel)

$serial = New-SerialPort -Name $Port -Rate $BaudRate

try {
  $serial.Open()
  Start-Sleep -Seconds 1

  $paused = $false
  $pendingCalibration = $false
  if ($Calibrate) {
    $serial.Write('c')
    $pendingCalibration = $true
    $paused = $true
    Write-Host 'Sent: c'
  } elseif (-not [string]::IsNullOrWhiteSpace($SendText)) {
    $serial.Write($SendText)
    Write-Host ("Sent: {0}" -f $SendText)
  }

  $quit = $false
  $interactiveKeysEnabled = $false
  try {
    $interactiveKeysEnabled = ($Host.Name -eq 'ConsoleHost') -and -not [Console]::IsInputRedirected
  } catch {
    $interactiveKeysEnabled = $false
  }
  $deadline = if ($DurationSeconds -gt 0) {
    [DateTime]::UtcNow.AddSeconds($DurationSeconds)
  } else {
    [DateTime]::MaxValue
  }

  while (-not $quit -and [DateTime]::UtcNow -lt $deadline) {
    if ($interactiveKeysEnabled) {
      while ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true).KeyChar
        switch ($key) {
          'p' {
            $paused = $true
            Write-Host "[paused]"
          }
          'r' {
            $paused = $false
            Write-Host "[resumed]"
          }
          'c' {
            $serial.Write('c')
            Write-Host "[sent c]"
          }
          'q' {
            $quit = $true
          }
        }
      }
    }

    try {
      $line = $serial.ReadLine().Trim()
    } catch [System.TimeoutException] {
      continue
    }

    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }

    if ($line.StartsWith('vector,')) {
      $levelLimit = if ($paused) { $PausedDisplayLevel } else { $DisplayLevel }
      if (Test-ShouldDisplayLine -Line $line -LevelLimit $levelLimit) {
        Write-Host $line
      }
      continue
    }

    $levelLimit = if ($paused) { $PausedDisplayLevel } else { $DisplayLevel }
    if (Test-ShouldDisplayLine -Line $line -LevelLimit $levelLimit) {
      Write-Host $line
    }

    if ($line -eq 'status,calibration_end') {
      Write-Host '[calibration complete]'
      $pendingCalibration = $false
      if ($paused) {
        $paused = $false
        Write-Host '[resumed]'
      }
    }

    if ($pendingCalibration -and $line -eq 'status,calibration_start') {
      Write-Host '[calibration running]'
    }
  }
}
finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  $serial.Dispose()
}
