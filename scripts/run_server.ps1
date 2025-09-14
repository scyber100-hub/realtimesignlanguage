param(
  [int]$Port = 8000,
  [string]$BindHost = "0.0.0.0"
)

$ErrorActionPreference = "Stop"

# Prefer local venv Python if available
$venvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
  & $venvPy -m uvicorn services.pipeline_server:app --host $BindHost --port $Port --reload
} else {
  python -m uvicorn services.pipeline_server:app --host $BindHost --port $Port --reload
}
