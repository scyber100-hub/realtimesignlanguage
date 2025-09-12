param(
  [int]$Port = 8000,
  [string]$Host = "0.0.0.0"
)

$ErrorActionPreference = "Stop"

python -m uvicorn services.pipeline_server:app --host $Host --port $Port --reload
