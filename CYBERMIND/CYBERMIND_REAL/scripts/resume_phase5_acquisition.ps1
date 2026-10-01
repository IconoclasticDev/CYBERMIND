$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = 'C:\Users\as030\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$datasetRoot = 'E:\Cybermind_dataset'
$deadline = '2026-10-05T23:59:59+05:30'

& $python (Join-Path $PSScriptRoot 'download_highspeed_window.py') `
    --root $datasetRoot `
    --workers 12 `
    --deadline $deadline
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

# The general downloader skips the first four archives after their verification
# manifests are published, then continues Feb 20, Feb 21, and Feb 23.
& $python (Join-Path $PSScriptRoot 'download_phase5_pcaps.py') `
    --root $datasetRoot `
    --workers 12 `
    --segment-mib 64
exit $LASTEXITCODE
