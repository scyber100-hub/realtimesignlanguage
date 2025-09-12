param(
  [string]$InputRtmp = "rtmp://origin/live/stream",
  [string]$InsetRtmp = "rtmp://localhost/unity/alpha",
  [string]$OutputRtmp = "rtmp://output/live/with_sign"
)

$cmd = @(
  'ffmpeg','-fflags','nobuffer','-threads','2',
  '-i', $InputRtmp,
  '-i', $InsetRtmp,
  '-filter_complex', '[1:v]scale=iw*0.25:ih*0.25 [pip]; [0:v][pip] overlay=W-w-40:H-h-40:format=auto',
  '-c:v', 'libx264','-preset','veryfast','-tune','zerolatency','-g','30','-keyint_min','30','-sc_threshold','0',
  '-c:a','aac','-b:a','128k','-f','flv', $OutputRtmp
)

Write-Host ($cmd -join ' ')
& $cmd
