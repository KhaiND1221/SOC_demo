<#
.SYNOPSIS
  Live-tail app.log, auth.log, nginx access.log and the postgres audit log
  in one window, pretty-printed and color-coded. For demo/observation only
  - does not change how logs are written.

.USAGE
  cd C:\Users\ANM-KHAIND8\soc-logging-lab
  .\watch-logs.ps1
  (Ctrl+C to stop)

  Shows the last few lines of history from each source on startup, then
  keeps streaming new lines as they're appended.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Sources = [ordered]@{
    "NGINX" = @{ Path = Join-Path $ProjectDir "logs\nginx\access.log"; Color = "Cyan";    Kind = "nginx" }
    "APP"   = @{ Path = Join-Path $ProjectDir "logs\app\app.log";      Color = "White";   Kind = "json" }
    "AUTH"  = @{ Path = Join-Path $ProjectDir "logs\app\auth.log";     Color = "Magenta"; Kind = "json" }
    "DB"    = @{ Path = $null;                                        Color = "Yellow";  Kind = "text" }
}

function Get-LatestPgLogPath {
    $pgDir = Join-Path $ProjectDir "logs\postgres"
    if (-not (Test-Path $pgDir)) { return $null }
    $f = Get-ChildItem $pgDir -Filter "*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($f) { return $f.FullName }
    return $null
}
$Sources["DB"].Path = Get-LatestPgLogPath

function Write-Tag {
    param([string]$Text, [string]$Color)
    Write-Host -NoNewline "["
    Write-Host -NoNewline $Text -ForegroundColor $Color
    Write-Host -NoNewline "] "
}

function Format-JsonLog {
    param([string]$Line)
    try { $o = $Line | ConvertFrom-Json } catch { Write-Host $Line -ForegroundColor DarkGray; return }

    $levelColor = switch ($o.level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        default   { "Green" }
    }
    $ts = try { ([datetimeoffset]$o.timestamp).UtcDateTime.ToString("HH:mm:ss") } catch { "--:--:--" }
    $uid = if ($o.user_id) { $o.user_id.ToString().Substring(0, [Math]::Min(8, $o.user_id.ToString().Length)) } else { "-" }

    Write-Host -NoNewline "$ts " -ForegroundColor DarkGray
    Write-Host -NoNewline ("{0,-7}" -f $o.level) -ForegroundColor $levelColor
    Write-Host -NoNewline " $($o.event)" -ForegroundColor White
    Write-Host -NoNewline "  user=$uid" -ForegroundColor DarkCyan
    Write-Host -NoNewline "  result=$($o.result)" -ForegroundColor $(if ($o.result -eq "fail") { "Red" } else { "DarkGreen" })
    Write-Host "  $($o.message)" -ForegroundColor Gray
}

function Format-NginxLog {
    param([string]$Line)
    try { $o = $Line | ConvertFrom-Json } catch { Write-Host $Line -ForegroundColor DarkGray; return }

    $statusColor = switch -Regex ($o.status.ToString()) {
        "^2" { "Green" }
        "^3" { "Cyan" }
        "^4" { "Yellow" }
        "^5" { "Red" }
        default { "White" }
    }
    Write-Host -NoNewline ("{0,-6} " -f $o.request_method) -ForegroundColor White
    Write-Host -NoNewline ("{0,-40} " -f $o.uri) -ForegroundColor Gray
    Write-Host -NoNewline "$($o.status) " -ForegroundColor $statusColor
    Write-Host "from $($o.remote_addr)" -ForegroundColor DarkGray
}

function Format-DbLog {
    param([string]$Line)

    # Postgres logs the full SQL statement (can wrap many terminal lines
    # with all its VALUES(...)). For the demo view, show just the verb +
    # table - the same compact single-line shape as the Nginx rows above.
    if ($Line -match 'statement:\s+(?<verb>INSERT|UPDATE|DELETE)\s+(?:INTO\s+|FROM\s+)?(?<table>\w+)') {
        $verb = $Matches['verb']
        $table = $Matches['table']
        $verbColor = switch ($verb) {
            "INSERT" { "Green" }
            "UPDATE" { "Cyan" }
            "DELETE" { "Red" }
            default  { "Yellow" }
        }
        Write-Host -NoNewline ("{0,-8} " -f $verb) -ForegroundColor $verbColor
        Write-Host ("{0,-20}" -f $table) -ForegroundColor Gray
    } else {
        # Non-DML lines (connection/checkpoint/startup messages, etc.)
        Write-Host $Line -ForegroundColor DarkGray
    }
}

function Write-LogLine {
    param([string]$Key, [hashtable]$Src, [string]$Line)
    Write-Tag -Text $Key -Color $Src.Color
    switch ($Src.Kind) {
        "json"  { Format-JsonLog -Line $Line }
        "nginx" { Format-NginxLog -Line $Line }
        "text"  { Format-DbLog -Line $Line }
    }
}

# Extracts a sortable timestamp from a raw log line so lines from all 4
# sources can be merged into ONE true chronological timeline instead of
# being grouped by source (which is confusing to read/demo).
function Get-LineTimestamp {
    param([string]$Line, [string]$Kind)
    try {
        switch ($Kind) {
            # Cast via [datetimeoffset] then take .UtcDateTime: JSON timestamps
            # carry an explicit +00:00 offset, and a plain [datetime] cast would
            # silently convert them to the machine's LOCAL timezone (e.g. +7),
            # which would desync them from the DB source's raw UTC-only text
            # timestamps and break the merge-sort below.
            "json"  { return ([datetimeoffset]($Line | ConvertFrom-Json).timestamp).UtcDateTime }
            "nginx" { return ([datetimeoffset]($Line | ConvertFrom-Json).time).UtcDateTime }
            "text"  {
                if ($Line -match '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ UTC') {
                    return [datetime]::ParseExact($Matches[0], "yyyy-MM-dd HH:mm:ss.fff 'UTC'", $null)
                }
                return [datetime]::MinValue
            }
        }
    } catch {
        return [datetime]::MinValue
    }
    return [datetime]::MinValue
}

function Read-NewLines {
    param([string]$Path, [string]$Key)
    if (-not $Path -or -not (Test-Path $Path)) { return @() }
    $len = (Get-Item $Path).Length
    if ($len -lt $Positions[$Key]) { $Positions[$Key] = 0 }
    if ($len -eq $Positions[$Key]) { return @() }

    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $fs.Seek($Positions[$Key], [System.IO.SeekOrigin]::Begin) | Out-Null
    $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
    $text = $sr.ReadToEnd()
    $Positions[$Key] = $fs.Position
    $sr.Close(); $fs.Close()

    return ($text -split "`r?`n") | Where-Object { $_ -ne "" }
}

# --- Startup: show the last few lines of history per source so the
#     window isn't blank, then remember the end-of-file position for
#     each source so the live loop only prints genuinely new lines. ---
$HistoryLines = 5
$Positions = @{}

Write-Host "=== Recent history (last $HistoryLines lines per source, merged by time) ===`n" -ForegroundColor DarkGray

$historyBatch = @()
foreach ($key in $Sources.Keys) {
    $src = $Sources[$key]
    $p = $src.Path
    if ($p -and (Test-Path $p)) {
        $recent = Get-Content -Path $p -Tail $HistoryLines -Encoding UTF8 -ErrorAction SilentlyContinue
        foreach ($line in $recent) {
            if ($line) {
                $historyBatch += [PSCustomObject]@{
                    Time = Get-LineTimestamp -Line $line -Kind $src.Kind
                    Key  = $key
                    Src  = $src
                    Line = $line
                }
            }
        }
        $Positions[$key] = (Get-Item $p).Length
    } else {
        $Positions[$key] = 0
    }
}
foreach ($item in ($historyBatch | Sort-Object Time)) {
    Write-LogLine -Key $item.Key -Src $item.Src -Line $item.Line
}

Write-Host "`n=== Live tail (Ctrl+C to stop) ===`n" -ForegroundColor DarkGray

while ($true) {
    $Sources["DB"].Path = Get-LatestPgLogPath

    $batch = @()
    foreach ($key in $Sources.Keys) {
        $src = $Sources[$key]
        $lines = Read-NewLines -Path $src.Path -Key $key
        foreach ($line in $lines) {
            $batch += [PSCustomObject]@{
                Time = Get-LineTimestamp -Line $line -Kind $src.Kind
                Key  = $key
                Src  = $src
                Line = $line
            }
        }
    }

    if ($batch.Count -gt 0) {
        foreach ($item in ($batch | Sort-Object Time)) {
            Write-LogLine -Key $item.Key -Src $item.Src -Line $item.Line
        }
    }

    Start-Sleep -Milliseconds 300
}
