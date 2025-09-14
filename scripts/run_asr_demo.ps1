param(
  [string]$Text = "안녕하세요 한국 날씨 방송",
  [int]$Port = 8000,
  [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = 'Stop'

function Wait-Health($url, $timeoutSec=25) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  return $false
}

# Start server in a new PowerShell window if not already running
Write-Host "Starting server on ${BindHost}:$Port ..."
Start-Process powershell -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","`"$PSScriptRoot\run_server.ps1`"","-Port",$Port,"-Host","$BindHost" | Out-Null

$ok = Wait-Health -url "http://${BindHost}:$Port/healthz" -timeoutSec 25
if (-not $ok) { Write-Warning "Server health check failed; continuing anyway..." }

Write-Host "Subscribing to /ws/timeline ..."
Start-Process powershell -ArgumentList "-NoProfile","-Command","`"$PSScriptRoot/../.venv/Scripts/python.exe`" `"$PSScriptRoot/example_ws_client.py`"" | Out-Null

Start-Sleep -Seconds 1

Write-Host "Streaming incremental text to /ws/ingest ..."
& "$PSScriptRoot/../.venv/Scripts/python.exe" "$PSScriptRoot/mock_asr_stream.py" --text $Text

Write-Host "Done. Check the timeline subscriber window."
