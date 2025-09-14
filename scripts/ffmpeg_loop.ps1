param(
  [string]$InputRtmp = "rtmp://origin/live/stream",
  [string]$InsetRtmp = "rtmp://localhost/unity/alpha",
  [string]$OutputRtmp = "rtmp://output/live/with_sign",
  [int]$MaxBackoffSec = 30
)

$ErrorActionPreference = 'Stop'

function Now { Get-Date -Format "yyyy-MM-dd HH:mm:ss" }

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Error "ffmpeg not found in PATH. Please install FFmpeg first."; exit 2
}

$backoff = 1
while ($true) {
  $cmd = @(
    'ffmpeg','-hide_banner','-nostdin','-fflags','nobuffer','-threads','2',
    '-i', $InputRtmp,
    '-i', $InsetRtmp,
    '-filter_complex', '[1:v]scale=iw*0.25:ih*0.25 [pip]; [0:v][pip] overlay=W-w-40:H-h-40:format=auto',
    '-c:v', 'libx264','-preset','veryfast','-tune','zerolatency','-g','30','-keyint_min','30','-sc_threshold','0',
    '-c:a','aac','-b:a','128k','-f','flv', $OutputRtmp
  )
  Write-Host "$(Now) starting ffmpeg: $($cmd -join ' ')"
  & $cmd
  $code = $LASTEXITCODE
  Write-Warning "$(Now) ffmpeg exited with code $code; restarting in $backoff sec..."
  Start-Sleep -Seconds $backoff
  $backoff = [Math]::Min($MaxBackoffSec, [Math]::Max(1, $backoff * 2))
}

