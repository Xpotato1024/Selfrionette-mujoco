<#
.SYNOPSIS
  Plot loadcell vector lines from firmware logs.

.DESCRIPTION
  Reads `vector,...` lines from a log file, standard input, or the clipboard.
  Generates a CSV export and a PNG chart without external Python dependencies.

  The chart plots the seven channel values against the sample index by default.
  If timestamp parsing succeeds, the CSV also includes the raw timestamp_ms.

.PARAMETER InputPath
  Optional path to a text log file. If omitted, the script reads from standard
  input unless -Clipboard is used.

.PARAMETER OutputPath
  Optional PNG output path. Default: derived from InputPath or the current time.

.PARAMETER CsvPath
  Optional CSV output path. Default: derived from OutputPath.

.PARAMETER Clipboard
  Read the source text from the clipboard instead of a file or stdin.

.PARAMETER Title
  Optional chart title.

.PARAMETER Channels
  Optional channel list to plot. Default: all channels 0..6.

.PARAMETER Help
  Print help and exit.

.EXAMPLE
  Get-Content .\logs\loadcell.txt | .\scripts\plot_loadcell_vectors.ps1

.EXAMPLE
  .\scripts\plot_loadcell_vectors.ps1 -InputPath .\logs\loadcell.txt

.EXAMPLE
  .\scripts\plot_loadcell_vectors.ps1 -Clipboard

.EXAMPLE
  .\scripts\plot_loadcell_vectors.ps1 -InputPath .\logs\loadcell.txt -OutputPath .\plots\loadcell.png
#>
param(
  [string]$InputPath,
  [string]$OutputPath,
  [string]$CsvPath,
  [switch]$Clipboard,
  [string]$Title = 'Loadcell vectors',
  [int[]]$Channels = @(0, 1, 2, 3, 4, 5, 6),
  [switch]$Help
)

$ErrorActionPreference = 'Stop'
$PipelineText = (@($input) -join "`n")

if ($Help) {
  Get-Help -Detailed $PSCommandPath
  exit 0
}

function Read-SourceText {
  if ($Clipboard) {
    return (Get-Clipboard -Raw)
  }

  if ($InputPath) {
    return (Get-Content -LiteralPath $InputPath -Raw)
  }

  if (-not [string]::IsNullOrWhiteSpace($PipelineText)) {
    return $PipelineText
  }

  return ([Console]::In.ReadToEnd())
}

function Parse-VectorLine {
  param([string]$Line)

  if (-not $Line.StartsWith('vector,')) {
    return $null
  }

  $parts = $Line.Split(',')
  if ($parts.Count -lt 9) {
    return $null
  }

  $timestamp = $null
  if (-not [long]::TryParse($parts[1], [ref]$timestamp)) {
    $timestamp = $null
  }

  $values = New-Object double[] 7
  for ($i = 0; $i -lt 7; $i++) {
    $value = 0.0
    if (-not [double]::TryParse($parts[$i + 2], [ref]$value)) {
      $value = [double]::NaN
    }
    $values[$i] = $value
  }

  [pscustomobject]@{
    Timestamp = $timestamp
    Values = $values
  }
}

function Ensure-Directory {
  param([string]$Path)

  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }
}

function Get-DefaultOutputPath {
  param([string]$SourcePath)

  if ($SourcePath) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($SourcePath)
    $dir = Split-Path -Parent $SourcePath
    return (Join-Path $dir ($base + '.png'))
  }

  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  return (Join-Path (Get-Location) ("loadcell-vectors-{0}.png" -f $stamp))
}

function Get-DefaultCsvPath {
  param([string]$PngPath)

  return ([System.IO.Path]::ChangeExtension($PngPath, '.csv'))
}

function Add-ChartSeries {
  param(
    $Chart,
    [int]$Channel
  )

  $series = New-Object System.Windows.Forms.DataVisualization.Charting.Series ("ch{0}" -f $Channel)
  $series.ChartType = [System.Windows.Forms.DataVisualization.Charting.SeriesChartType]::Line
  $series.BorderWidth = 2
  $series.XValueType = [System.Windows.Forms.DataVisualization.Charting.ChartValueType]::Int32
  $series.YValueType = [System.Windows.Forms.DataVisualization.Charting.ChartValueType]::Double
  [void]$Chart.Series.Add($series)
  return $series
}

$sourceText = Read-SourceText
$records = New-Object System.Collections.Generic.List[object]

foreach ($line in ($sourceText -split "`r?`n")) {
  $record = Parse-VectorLine -Line $line.Trim()
  if ($null -ne $record) {
    [void]$records.Add($record)
  }
}

if ($records.Count -eq 0) {
  throw 'No vector lines were found.'
}

if (-not $OutputPath) {
  $OutputPath = Get-DefaultOutputPath -SourcePath $InputPath
}

if (-not $CsvPath) {
  $CsvPath = Get-DefaultCsvPath -PngPath $OutputPath
}

Ensure-Directory -Path $OutputPath
Ensure-Directory -Path $CsvPath

$csvRows = foreach ($recordIndex in 0..($records.Count - 1)) {
  $record = $records[$recordIndex]
  $row = [ordered]@{
    sample_index = $recordIndex
    timestamp_ms = $record.Timestamp
  }

  for ($ch = 0; $ch -lt 7; $ch++) {
    $row["ch$ch"] = [double]$record.Values[$ch]
  }

  [pscustomobject]$row
}

$csvRows | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $CsvPath

[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms.DataVisualization')
[void][System.Reflection.Assembly]::LoadWithPartialName('System.Drawing')

$chart = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
$chart.Width = 1600
$chart.Height = 900
$chart.BackColor = [System.Drawing.Color]::White

$area = New-Object System.Windows.Forms.DataVisualization.Charting.ChartArea 'Main'
$area.AxisX.Title = 'Sample index'
$area.AxisY.Title = 'Value'
$area.AxisX.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
$area.AxisY.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
$area.AxisX.LabelStyle.Angle = -45
$area.AxisY.LabelStyle.Format = '0'
$chart.ChartAreas.Add($area)

$legend = New-Object System.Windows.Forms.DataVisualization.Charting.Legend 'Legend'
$legend.Docking = 'Top'
$chart.Legends.Add($legend)

$chart.Titles.Add($Title) | Out-Null

$palette = @(
  [System.Drawing.Color]::FromArgb(31, 119, 180),
  [System.Drawing.Color]::FromArgb(255, 127, 14),
  [System.Drawing.Color]::FromArgb(44, 160, 44),
  [System.Drawing.Color]::FromArgb(214, 39, 40),
  [System.Drawing.Color]::FromArgb(148, 103, 189),
  [System.Drawing.Color]::FromArgb(140, 86, 75),
  [System.Drawing.Color]::FromArgb(23, 190, 207)
)

foreach ($channel in $Channels) {
  if ($channel -lt 0 -or $channel -gt 6) {
    continue
  }

  $chartSeries = Add-ChartSeries -Chart $chart -Channel $channel
  $chartSeries.ChartArea = 'Main'
  $chartSeries.Legend = 'Legend'
  $chartSeries.Color = $palette[$channel % $palette.Count]

  for ($i = 0; $i -lt $records.Count; $i++) {
    $x = [double]$i
    $y = [double]$records[$i].Values[$channel]
    [void]$chartSeries.Points.AddXY($x, $y)
  }
}

if ($records.Count -gt 0) {
  $chartAreas = $chart.ChartAreas['Main']
  $chartAreas.AxisX.Minimum = 0
  $chartAreas.AxisX.Maximum = [Math]::Max(0, $records.Count - 1)
}

$bitmap = New-Object System.Drawing.Bitmap($chart.Width, $chart.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::White)
$chart.DrawToBitmap($bitmap, (New-Object System.Drawing.Rectangle 0, 0, $chart.Width, $chart.Height))
$bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$graphics.Dispose()
$bitmap.Dispose()
$chart.Dispose()

Write-Host ("Parsed vectors : {0}" -f $records.Count)
Write-Host ("PNG output     : {0}" -f $OutputPath)
Write-Host ("CSV output     : {0}" -f $CsvPath)
