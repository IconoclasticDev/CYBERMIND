$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:CYBERMIND_ROLLOUT_STEPS = "4"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 50068
