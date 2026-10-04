param(
    [string]$DockerExe = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe",
    [string]$PythonExe = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    [switch]$PreflightOnly
)

# Run locally after manually disconnecting physical network connections.
# This script never changes adapters, pulls images, rebuilds, deletes volumes,
# forces container recreation, or pushes Git changes.
$ErrorActionPreference = 'Stop'
$releaseRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$releaseManifestPath = Join-Path $releaseRepo 'CYBERMIND\releases\CYBERMIND_DOCKER_DESKTOP_ATTACK_LAB_2026-10-04.manifest.json'
$releaseManifest = Get-Content -LiteralPath $releaseManifestPath -Raw | ConvertFrom-Json
$releaseZipPath = Join-Path $releaseRepo $releaseManifest.zip
$releaseVerifier = Join-Path $PSScriptRoot 'verify_offline_release_api.py'
foreach ($releaseInput in @($DockerExe, $PythonExe, $releaseZipPath, $releaseVerifier)) {
    if (-not (Test-Path -LiteralPath $releaseInput -PathType Leaf)) { throw "Required local file missing: $releaseInput" }
}
$releaseZipActual = (Get-FileHash -LiteralPath $releaseZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($releaseZipActual -ne $releaseManifest.sha256) { throw 'ZIP SHA-256 mismatch' }
Write-Output "Verified ZIP SHA-256: $releaseZipActual"
if ($PreflightOnly) {
    Write-Output 'PASS: local test dependencies and release ZIP integrity. No launch or network-off test performed.'
    exit 0
}

$releaseAdapters = @(Get-NetAdapter -Physical | Select-Object Name, Status)
if ($releaseAdapters.Count -eq 0) { throw 'Cannot prove offline state: no physical adapters returned' }
if (@($releaseAdapters | Where-Object Status -eq 'Up').Count -gt 0) {
    throw 'Physical network is connected. Disconnect Wi-Fi/Ethernet manually, then run this script again.'
}
$releaseStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$releaseOutput = Join-Path $releaseRepo "tmp\release_2026-10-04\offline_$releaseStamp"
New-Item -ItemType Directory -Path $releaseOutput | Out-Null
$releaseNetworkLog = Join-Path $releaseOutput 'network-samples.jsonl'
$releaseSummary = [ordered]@{ started_utc=(Get-Date).ToUniversalTime().ToString('o'); result='INCOMPLETE'; zip_sha256=$releaseZipActual; checks=@{} }
$releaseMonitor = $null
$releaseTranscript = $false

function Invoke-ReleaseDocker {
    param([string[]]$CommandArgs)
    Write-Output ('COMMAND: docker ' + ($CommandArgs -join ' '))
    & $DockerExe @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)" }
}

try {
    Start-Transcript -LiteralPath (Join-Path $releaseOutput 'commands.txt') | Out-Null
    $releaseTranscript = $true
    $releaseMonitor = Start-Job -ArgumentList $releaseNetworkLog -ScriptBlock {
        param($networkPath)
        while ($true) {
            try {
                $adapters = @(Get-NetAdapter -Physical -ErrorAction Stop | Select-Object Name, Status)
                $record = @{utc=(Get-Date).ToUniversalTime().ToString('o'); adapters=$adapters; connected=(@($adapters | Where-Object Status -eq 'Up').Count -gt 0); observed=($adapters.Count -gt 0)}
            } catch { $record = @{utc=(Get-Date).ToUniversalTime().ToString('o'); observed=$false; error=$_.Exception.Message} }
            $record | ConvertTo-Json -Depth 4 -Compress | Add-Content -LiteralPath $networkPath
            Start-Sleep -Seconds 1
        }
    }
    Expand-Archive -LiteralPath $releaseZipPath -DestinationPath (Join-Path $releaseOutput 'extracted')
    $releaseFolder = Join-Path $releaseOutput ('extracted\' + $releaseManifest.release)
    $releaseFiles = Get-Content -LiteralPath (Join-Path $releaseFolder 'release.manifest.json') -Raw | ConvertFrom-Json
    foreach ($releaseFile in $releaseFiles.files) {
        $actual = (Get-FileHash -LiteralPath (Join-Path $releaseFolder $releaseFile.path) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $releaseFile.sha256) { throw "Extracted file mismatch: $($releaseFile.path)" }
        Write-Output "SHA256 $actual  $($releaseFile.path)"
    }
    $releaseSummary.checks.extracted_integrity = 'PASS'
    Invoke-ReleaseDocker -CommandArgs @('load','-i',(Join-Path $releaseFolder 'images\cybermind-offline-app.tar'))
    $releaseCurrent = @(& $DockerExe ps -a --filter 'name=^/cybermind-offline-cybermind-1$' --format '{{.Image}}')
    if ($releaseCurrent.Count -gt 0) {
        $releaseContainerImage = & $DockerExe inspect cybermind-offline-cybermind-1 --format '{{.Image}}'
        if ($releaseContainerImage -ne $releaseManifest.image_id) { throw 'Existing container uses another image; stop its old release before testing. No forced recreation performed.' }
        Invoke-ReleaseDocker -CommandArgs @('stop','cybermind-offline-cybermind-1')
        $releaseStopped = & $DockerExe inspect cybermind-offline-cybermind-1 --format '{{.State.Running}}'
        if ($releaseStopped -ne 'false') { throw 'Release container did not stop before offline launch' }
    }
    Write-Output "COMMAND: Start-Process $releaseFolder\CYBERMIND.exe"
    Start-Process -FilePath (Join-Path $releaseFolder 'CYBERMIND.exe') -WorkingDirectory $releaseFolder
    $releaseDeadline = (Get-Date).AddSeconds(180)
    $releaseBase = $null
    do {
        $releasePort = $null
        try {
            $releasePort = & $DockerExe compose -p cybermind-offline -f (Join-Path $releaseFolder 'compose.offline.yaml') port cybermind 8000 2>$null
            if ($LASTEXITCODE -ne 0) { $releasePort = $null }
        } catch {
            # Compose reports a stopped service while the desktop launcher starts it.
            # Keep polling until the existing deadline; never restart from this check.
            $releasePort = $null
        }
        if ($releasePort -match '^127\.0\.0\.1:\d+$') {
            try {
                $health = Invoke-RestMethod "http://$releasePort/api/health" -TimeoutSec 2
                if ($health.status -eq 'ok' -and $health.model.available) { $releaseBase = "http://$releasePort"; break }
            } catch {}
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $releaseDeadline)
    if (-not $releaseBase) { throw 'Offline desktop launcher/API health timed out' }
    $releaseSummary.checks.launch_health = 'PASS'
    $releaseSummary.checks.start_from_stopped_container = 'PASS'
    $releaseSummary.base = $releaseBase
    Write-Output "COMMAND: python verify_offline_release_api.py --base $releaseBase --pcap bundled-demo --output api-results.json"
    & $PythonExe $releaseVerifier --base $releaseBase --pcap (Join-Path $releaseFolder 'demo\cic2018_feb28_victim_scan_15min.pcap') --output (Join-Path $releaseOutput 'api-results.json')
    if ($LASTEXITCODE -ne 0) { throw 'Offline API verification failed; inspect api-results.json' }
    $releaseSummary.checks.pcap_forecast_comparison_validation_four_lab_loops = 'PASS'
    $releaseApiEvidence = Get-Content -LiteralPath (Join-Path $releaseOutput 'api-results.json') -Raw | ConvertFrom-Json
    $releasePersistedRun = $releaseApiEvidence.checks.local_validation
    if (-not $releasePersistedRun.run_id) { throw 'No validation record available for persistence check' }
    $releaseRunsBefore = Invoke-RestMethod "$releaseBase/api/validation/local" -TimeoutSec 10
    $releaseRunsBefore | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $releaseOutput 'records-before-stop.json') -Encoding utf8
    Invoke-ReleaseDocker -CommandArgs @('stop','cybermind-offline-cybermind-1')
    Invoke-ReleaseDocker -CommandArgs @('compose','-p','cybermind-offline','-f',(Join-Path $releaseFolder 'compose.offline.yaml'),'up','-d','--pull','never')
    $releaseRelaunchReady = $false
    $releaseRelaunchDeadline = (Get-Date).AddSeconds(180)
    do {
        try {
            $releaseRelaunchPort = & $DockerExe compose -p cybermind-offline -f (Join-Path $releaseFolder 'compose.offline.yaml') port cybermind 8000 2>$null
            if ($LASTEXITCODE -ne 0 -or $releaseRelaunchPort -notmatch '^127\.0\.0\.1:\d+$') { throw 'Relaunch loopback port not ready' }
            $releaseBase = "http://$releaseRelaunchPort"
            $releaseRelaunchHealth = Invoke-RestMethod "$releaseBase/api/health" -TimeoutSec 2
            if ($releaseRelaunchHealth.status -eq 'ok' -and $releaseRelaunchHealth.model.available) { $releaseRelaunchReady = $true; break }
        } catch {}
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $releaseRelaunchDeadline)
    if (-not $releaseRelaunchReady) { throw 'Release did not become healthy after stop/relaunch' }
    $releaseSummary.relaunch_base = $releaseBase
    $releaseRunsAfter = Invoke-RestMethod "$releaseBase/api/validation/local" -TimeoutSec 10
    $releaseRunsAfter | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $releaseOutput 'records-after-relaunch.json') -Encoding utf8
    $releaseMatchedRun = @($releaseRunsAfter.runs | Where-Object run_id -eq $releasePersistedRun.run_id)
    if ($releaseMatchedRun.Count -ne 1) { throw 'Validation record missing or duplicated after stop/relaunch' }
    if (($releaseMatchedRun[0] | ConvertTo-Json -Depth 20 -Compress) -ne ($releasePersistedRun | ConvertTo-Json -Depth 20 -Compress)) { throw 'Persisted validation record changed after stop/relaunch' }
    $releaseSummary.checks.stop_relaunch_record_persistence = 'PASS'
    $releaseSummary.persisted_run_id = $releasePersistedRun.run_id
    $releaseSamples = @(Get-Content -LiteralPath $releaseNetworkLog | ForEach-Object { $_ | ConvertFrom-Json })
    if ($releaseSamples.Count -eq 0 -or @($releaseSamples | Where-Object { $_.connected -or -not $_.observed }).Count -gt 0) {
        throw 'Network-off proof failed: physical connection or unobservable adapter state during test'
    }
    $releaseSummary.checks.physical_network_disconnected_during_test = 'PASS'
    $releaseSummary.network_samples = $releaseSamples.Count
    $releaseSummary.result = 'PASS: offline launch and API flow; UI encryption/decryption remains a separate check'
} catch {
    $releaseSummary.result = 'FAIL'
    $releaseSummary.error = $_.Exception.Message
    Write-Output "FAILED: $($_.Exception.Message)"
} finally {
    if ($releaseMonitor) { Stop-Job $releaseMonitor; Receive-Job $releaseMonitor -ErrorAction Continue | Out-Null }
    $releaseSummary.finished_utc = (Get-Date).ToUniversalTime().ToString('o')
    $releaseSummary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $releaseOutput 'summary.json') -Encoding utf8
    Write-Output "RESULT: $($releaseSummary.result)"
    Write-Output "Logs saved to: $releaseOutput"
    Write-Output 'You may reconnect Wi-Fi now. The test does not change your network settings.'
    if ($releaseTranscript) { Stop-Transcript | Out-Null }
}
if ($releaseSummary.result -eq 'FAIL') { exit 1 }
