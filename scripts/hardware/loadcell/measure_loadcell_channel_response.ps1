<#
.SYNOPSIS
  Measure one loadcell response against a baseline, or sweep all sensors.

.DESCRIPTION
  Opens a serial port, captures a baseline window, then measures a selected
  sensor once or repeats / sweeps sensors 1..7. It prints per-channel means
  and strongest responses for quick manual mapping.

.PARAMETER Port
  Serial port name to open. Default: COM5.

.PARAMETER BaudRate
  Baud rate for the serial connection. Default: 115200.

.PARAMETER BaselineSeconds
  Seconds to spend capturing the baseline window. Default: 3.

.PARAMETER PressSeconds
  Seconds to spend capturing the press window. Default: 4.

.PARAMETER AllSensors
  Measure sensors 1..7 sequentially after the baseline window.

.PARAMETER Sensor
  Human-facing sensor number to measure when not sweeping. Default: 1.

.PARAMETER Repeats
  Repeat the same sensor measurement this many times.

.EXAMPLE
  .\scripts\hardware\loadcell\measure_loadcell_channel_response.ps1 -Port COM5

.EXAMPLE
  .\scripts\hardware\loadcell\measure_loadcell_channel_response.ps1 -Port COM5 -AllSensors

.EXAMPLE
  .\scripts\hardware\loadcell\measure_loadcell_channel_response.ps1 -Port COM5 -Sensor 4 -Repeats 3
#>
param(
  [string]$Port = 'COM5',
  [int]$BaudRate = 115200,
  [int]$BaselineSeconds = 3,
  [int]$PressSeconds = 4,
  [switch]$AllSensors,
  [ValidateRange(1, 7)]
  [int]$Sensor = 1,
  [int]$Repeats = 1
)

$ErrorActionPreference = 'Stop'

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

function Read-Phase {
  param(
    [System.IO.Ports.SerialPort]$SerialPort,
    [string]$Label,
    [int]$Seconds
  )

  $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
  $rows = New-Object 'System.Collections.Generic.List[object]'

  Write-Host ""
  Write-Host "[$Label] $Seconds seconds"

  while ([DateTime]::UtcNow -lt $deadline) {
    try {
      $line = $SerialPort.ReadLine().Trim()
    } catch [System.TimeoutException] {
      continue
    }

    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }

    if ($line.StartsWith('vector,')) {
      $parts = $line.Split(',')
      if ($parts.Count -eq 9) {
        try {
          $row = [pscustomobject]@{
            Ts = [int64]$parts[1]
            V0 = [double]$parts[2]
            V1 = [double]$parts[3]
            V2 = [double]$parts[4]
            V3 = [double]$parts[5]
            V4 = [double]$parts[6]
            V5 = [double]$parts[7]
            V6 = [double]$parts[8]
          }
          $rows.Add($row) | Out-Null
        } catch {
          # Ignore malformed vector rows and keep streaming.
        }
      }
      continue
    }

    if ($line.StartsWith('status,') -or $line.StartsWith('warn,')) {
      Write-Host $line
    }
  }

  return $rows
}

function Get-ChannelMeans {
  param(
    [object[]]$Rows
  )

  $result = @()
  foreach ($idx in 0..6) {
    $values = foreach ($row in $Rows) {
      $row.("V$idx")
    }
    $mean = if ($values.Count -gt 0) { ($values | Measure-Object -Average).Average } else { 0.0 }
    $result += [pscustomobject]@{
      Channel = $idx
      Mean = [double]$mean
    }
  }
  return $result
}

function Show-Summary {
  param(
    [object[]]$BaselineRows,
    [object[]]$PressRows
  )

  $baselineMeans = Get-ChannelMeans -Rows $BaselineRows
  $pressMeans = Get-ChannelMeans -Rows $PressRows

  $summary = for ($idx = 0; $idx -lt 7; $idx++) {
    $base = $baselineMeans[$idx].Mean
    $press = $pressMeans[$idx].Mean
    $delta = $press - $base
    [pscustomobject]@{
      Channel = $idx
      BaselineMean = [math]::Round($base, 2)
      PressMean = [math]::Round($press, 2)
      Delta = [math]::Round($delta, 2)
      AbsDelta = [math]::Abs([math]::Round($delta, 2))
    }
  }

  $sorted = $summary | Sort-Object AbsDelta -Descending

  Write-Host ""
  Write-Host "=== Channel summary ==="
  $summary | Format-Table -AutoSize | Out-Host

  $top = $sorted | Select-Object -First 3
  Write-Host ""
  Write-Host "=== Strongest responses ==="
  $top | Format-Table -AutoSize | Out-Host

  return $sorted
}

function Get-StrongestChannel {
  param(
    [object[]]$SummaryRows
  )

  return $SummaryRows | Select-Object -First 1
}

function Read-SensorMeasurement {
  param(
    [System.IO.Ports.SerialPort]$SerialPort,
    [object[]]$BaselineRows,
    [int]$SensorNumber,
    [int]$PressSeconds
  )

  Write-Host ""
  Write-Host ("Step: press load cell #{0}, then press Enter." -f $SensorNumber)
  [void](Read-Host)
  $pressRows = Read-Phase -SerialPort $SerialPort -Label ("press#{0}" -f $SensorNumber) -Seconds $PressSeconds
  $summary = Show-Summary -BaselineRows $BaselineRows -PressRows $pressRows
  $strongest = Get-StrongestChannel -SummaryRows $summary

  return [pscustomobject]@{
    Sensor = $SensorNumber
    Channel = $strongest.Channel
    AbsDelta = $strongest.AbsDelta
    Delta = $strongest.Delta
  }
}

Write-Host "Opening $Port at $BaudRate baud."
Write-Host "Close any existing monitor on the same port before continuing."

$serial = New-SerialPort -Name $Port -Rate $BaudRate

try {
  $serial.Open()
  Start-Sleep -Seconds 1

  Write-Host ""
  Write-Host "Step 1: keep all load cells untouched, then press Enter."
  [void](Read-Host)
  $baselineRows = Read-Phase -SerialPort $serial -Label "baseline" -Seconds $BaselineSeconds

  if ($AllSensors) {
    $results = New-Object 'System.Collections.Generic.List[object]'

    for ($sensor = 1; $sensor -le 7; $sensor++) {
      $results.Add((Read-SensorMeasurement -SerialPort $serial -BaselineRows $baselineRows -SensorNumber $sensor -PressSeconds $PressSeconds)) | Out-Null
    }

    Write-Host ""
    Write-Host "=== Final mapping summary ==="
    $results | Format-Table -AutoSize | Out-Host
  } elseif ($Repeats -gt 1) {
    $results = New-Object 'System.Collections.Generic.List[object]'

    for ($i = 1; $i -le $Repeats; $i++) {
      Write-Host ""
      Write-Host ("Repeat {0}/{1}" -f $i, $Repeats)
      $results.Add((Read-SensorMeasurement -SerialPort $serial -BaselineRows $baselineRows -SensorNumber $Sensor -PressSeconds $PressSeconds)) | Out-Null
    }

    Write-Host ""
    Write-Host "=== Repeated mapping summary ==="
    $results | Format-Table -AutoSize | Out-Host
  } else {
    $null = Read-SensorMeasurement -SerialPort $serial -BaselineRows $baselineRows -SensorNumber $Sensor -PressSeconds $PressSeconds
  }
}
finally {
  if ($serial.IsOpen) {
    $serial.Close()
  }
  $serial.Dispose()
}
