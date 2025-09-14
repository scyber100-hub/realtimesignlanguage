$ErrorActionPreference = 'SilentlyContinue'

Write-Host "Listing related processes..."
$procs = Get-CimInstance Win32_Process | Where-Object {
  ($_.CommandLine -match 'uvicorn|pipeline_server|example_ws_client|run_server\.ps1|mock_asr_stream|wav_ws_stream|whisper_ingest_from') -or
  ($_.ExecutablePath -like '*realtimesignlanguage*')
}
$procs | Select-Object ProcessId, Name, CommandLine | Format-List

Write-Host "`nStopping processes..."
foreach ($p in $procs) {
  try {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
    Write-Host "Stopped PID" $p.ProcessId $p.Name
  } catch {
    Write-Host "Skip PID" $p.ProcessId $p.Name ":" $_.Exception.Message
  }
}

Write-Host "`nChecking port 8000..."
try {
  Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction Stop | Select-Object -First 5
} catch {
  try { netstat -ano | findstr :8000 } catch {}
}

Write-Host "Done."

