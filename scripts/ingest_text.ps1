param(
  [string]$Text = "안녕하세요 한국 날씨",
  [string]$Url = "http://localhost:8000/ingest_text"
)

$body = @{ text = $Text } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post -Uri $Url -Body $body -ContentType 'application/json; charset=utf-8'
