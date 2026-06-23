$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
python (Join-Path $PSScriptRoot "server.py") --host 127.0.0.1 --port 8051
