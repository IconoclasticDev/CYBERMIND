param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$releaseName = 'CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04'
$archivePath = Join-Path $projectDir "releases\$releaseName.zip"
$manifest = Get-Content -LiteralPath (Join-Path $projectDir "releases\$releaseName.manifest.json") -Raw | ConvertFrom-Json
$runtimeDir = Join-Path $projectDir '.runtime'
$targetDir = Join-Path $runtimeDir $releaseName
$markerPath = Join-Path $targetDir '.archive-sha256'
$ready = (Test-Path -LiteralPath $markerPath) -and ((Get-Content -LiteralPath $markerPath -Raw).Trim() -eq $manifest.sha256) -and (Test-Path -LiteralPath (Join-Path $targetDir 'CYBERMIND.exe')) -and (Test-Path -LiteralPath (Join-Path $targetDir 'images\cybermind-offline-app.tar'))
if (-not $ready) {
    $isPointer = (-not (Test-Path -LiteralPath $archivePath)) -or ((Get-Item -LiteralPath $archivePath).Length -lt 1024)
    if ($isPointer) {
        Write-Host 'Preparing the real release archive. This first download requires internet; later launches are local.'
        $downloadPath = "$archivePath.download"
        Invoke-WebRequest -Uri "https://media.githubusercontent.com/media/IconoclasticDev/CYBERMIND/main/CYBERMIND/releases/$releaseName.zip" -OutFile $downloadPath -UseBasicParsing
        if ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256) { throw 'Downloaded archive failed its SHA-256 check. It may not have been published yet.' }
        Move-Item -LiteralPath $downloadPath -Destination $archivePath -Force
    }
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256) { throw 'Release archive failed its SHA-256 check. Replace it with the current complete release.' }
    Write-Host 'Preparing CYBERMIND. Please wait while the bundled files are extracted.'
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDir -Force
    foreach ($relativePath in @('CYBERMIND.exe','images\cybermind-offline-app.tar','compose.offline.yaml','ui\index.html')) {
        if (-not (Test-Path -LiteralPath (Join-Path $targetDir $relativePath))) { throw "Release file is missing: $relativePath" }
    }
    Set-Content -LiteralPath $markerPath -Value $manifest.sha256 -Encoding ASCII
}
if ($PrepareOnly) { Write-Host "Verified release ready at $targetDir"; exit 0 }
Write-Host 'Opening CYBERMIND. Docker Desktop must be installed; the application handles Docker startup.'
Start-Process -FilePath (Join-Path $targetDir 'CYBERMIND.exe') -WorkingDirectory $targetDir
