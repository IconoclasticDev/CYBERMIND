param(
    [Parameter(Mandatory=$true)][string]$Video,
    [Parameter(Mandatory=$true)][string]$Output
)

Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([Uri]::new($Video))
$player.Play()
Start-Sleep -Seconds 2
$player.Pause()
$width = $player.NaturalVideoWidth
$height = $player.NaturalVideoHeight
$duration = $player.NaturalDuration.TimeSpan.TotalSeconds
Write-Output "width=$width height=$height duration=$duration"
if ($width -le 0 -or $height -le 0) { throw 'Windows Media Player did not decode the video.' }
$times = if ($duration -le 6) { @(0, 1, 2, 3) } else { @(0, 3, 6, 9, 12, 15, 20, 25, 30, 40, 50, 60) | Where-Object { $_ -lt $duration } }
$player.Position = [TimeSpan]::Zero
$player.Play()
$last = 0
foreach ($time in $times) {
    if ($time -gt $last) { Start-Sleep -Seconds ($time - $last) }
    $last = $time
    $visual = New-Object System.Windows.Media.DrawingVisual
    $context = $visual.RenderOpen()
    $context.DrawVideo($player, [Windows.Rect]::new(0, 0, $width, $height))
    $context.Close()
    $bitmap = New-Object System.Windows.Media.Imaging.RenderTargetBitmap($width, $height, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($visual)
    $encoder = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
    $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $path = Join-Path $Output ("frame_{0:D3}.png" -f $time)
    $stream = [System.IO.File]::Create($path)
    try { $encoder.Save($stream) } finally { $stream.Dispose() }
    Write-Output $path
}
$player.Close()
