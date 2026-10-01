param(
    [string]$Cutoff = "2026-09-21T07:23:30+05:30"
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project ".phase01-venv\Scripts\python.exe"
$root = "E:\Cybermind_dataset"
$manifest = Join-Path $root "manifests\2018-02-28.truncated-prefix.json"
$ejectRecord = Join-Path $root "manifests\eject_request.json"

& $python (Join-Path $PSScriptRoot "capture_contiguous_prefix.py") `
    --root $root `
    --cutoff $Cutoff `
    --workers 6
if ($LASTEXITCODE -ne 0) {
    throw "Contiguous-prefix finalizer exited $LASTEXITCODE; refusing unverified eject sequence"
}

$record = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
if (-not $record.contiguous_prefix -or $record.bytes -le 0 -or $record.sha256.Length -ne 64) {
    throw "Final prefix manifest is incomplete; refusing eject"
}

[ordered]@{
    requested_at_local = [datetime]::Now.ToString("o")
    drive = "E:"
    manifest = $manifest
    bytes = [int64]$record.bytes
    last_fully_written_byte_offset = [int64]$record.last_fully_written_byte_offset
    sha256 = $record.sha256
    write_handles_closed = $true
} | ConvertTo-Json | Set-Content -LiteralPath $ejectRecord -Encoding utf8

[GC]::Collect()
[GC]::WaitForPendingFinalizers()
$shell = New-Object -ComObject Shell.Application
$item = $shell.Namespace(17).ParseName("E:")
if ($null -eq $item) {
    throw "E: was not visible immediately before eject"
}
$item.InvokeVerb("Eject")
for ($attempt = 0; $attempt -lt 30 -and (Test-Path -LiteralPath "E:\"); $attempt++) {
    Start-Sleep -Seconds 1
}
if (Test-Path -LiteralPath "E:\") {
    & mountvol.exe E: /p
}
