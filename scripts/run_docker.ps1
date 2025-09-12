param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

docker build -t realtimesignlanguage/pipeline:local .
docker run --rm -it -p ${Port}:8000 realtimesignlanguage/pipeline:local

