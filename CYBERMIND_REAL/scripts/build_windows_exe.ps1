$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $root
if (-not (Test-Path 'web/dist/index.html')) { throw 'Build the React assets first: cd web; npm ci; npm run build' }
if (-not (Test-Path 'checkpoints/final_grouped/best.pt')) { throw 'Trusted model checkpoint is missing.' }
$python = Join-Path $root '.venv/Scripts/python.exe'
& $python -m PyInstaller --noconfirm --clean --onedir --name CYBERMIND --paths (Join-Path $root 'src') --collect-all torch_geometric --add-data "web/dist;web/dist" --add-data "examples/analyst_demo;examples/analyst_demo" --add-data "checkpoints/final_grouped/best.pt;checkpoints/final_grouped" scripts/launch_desktop.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Write-Host "Built $root/dist/CYBERMIND/CYBERMIND.exe"

