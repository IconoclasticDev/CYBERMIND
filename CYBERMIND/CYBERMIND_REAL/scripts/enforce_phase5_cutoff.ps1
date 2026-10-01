param(
    [datetime]$StopAt = "2026-09-21T07:21:30+05:30",
    [datetime]$Deadline = "2026-09-21T07:25:00+05:30"
)

$ErrorActionPreference = "SilentlyContinue"
$log = "E:\Cybermind_dataset\logs\cutoff_enforcer.log"
while ([datetime]::Now -lt $StopAt) {
    Start-Sleep -Milliseconds 200
}

$curlProcesses = Get-CimInstance Win32_Process -Filter "Name='curl.exe'" |
    Where-Object { $_.CommandLine -like '*E:\Cybermind_dataset\intermediate\contiguous_batch*' }
foreach ($process in $curlProcesses) {
    Stop-Process -Id $process.ProcessId
}
"$(Get-Date -Format o) stopped $(@($curlProcesses).Count) temporary-range workers; committed prefix was not open by curl" |
    Set-Content -LiteralPath $log -Encoding utf8

$manifest = "E:\Cybermind_dataset\manifests\2018-02-28.truncated-prefix.json"
while ([datetime]::Now -lt $Deadline -and -not (Test-Path -LiteralPath $manifest)) {
    Start-Sleep -Milliseconds 100
}
if (Test-Path -LiteralPath $manifest) {
    "$(Get-Date -Format o) final manifest present" | Add-Content -LiteralPath $log -Encoding utf8
} else {
    "$(Get-Date -Format o) ERROR final manifest absent at hard deadline" | Add-Content -LiteralPath $log -Encoding utf8
}
