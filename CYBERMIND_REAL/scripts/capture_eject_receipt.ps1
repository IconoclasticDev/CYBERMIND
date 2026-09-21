param(
    [string]$Source = "E:\Cybermind_dataset\manifests\2018-02-28.truncated-prefix.json",
    [string]$EjectSource = "E:\Cybermind_dataset\manifests\eject_request.json",
    [string]$DestinationDirectory = "D:\Abhinav\College\SIH\CYBERMIND_ONE_CLICK_128GB_PORTABLE\CYBERMIND_REAL\runtime\phase5_cutoff_receipt",
    [datetime]$Deadline = "2026-09-21T07:25:00+05:30"
)

$ErrorActionPreference = "SilentlyContinue"
New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
$receipt = Join-Path $DestinationDirectory "2018-02-28.truncated-prefix.json"
$ejectReceipt = Join-Path $DestinationDirectory "eject_request.json"
$watchLog = Join-Path $DestinationDirectory "receipt_watcher.log"

while ([datetime]::Now -lt $Deadline) {
    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination $receipt -Force
        if (Test-Path -LiteralPath $EjectSource) {
            Copy-Item -LiteralPath $EjectSource -Destination $ejectReceipt -Force
        }
        "$(Get-Date -Format o) final manifest copied before eject" | Set-Content -LiteralPath $watchLog -Encoding utf8
        exit 0
    }
    Start-Sleep -Milliseconds 20
}

"$(Get-Date -Format o) deadline reached without seeing final manifest" | Set-Content -LiteralPath $watchLog -Encoding utf8
exit 1
