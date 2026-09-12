$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $root "demo-data\atlas-audit\04-audio-recording-script.txt"
$outputPath = Join-Path $root "demo-data\atlas-audit\04-architecture-review.wav"
$speechText = Get-Content -Raw $scriptPath

$voice = New-Object -ComObject SAPI.SpVoice
$stream = New-Object -ComObject SAPI.SpFileStream
try {
    $stream.Open($outputPath, 3, $false)
    $voice.AudioOutputStream = $stream
    [void]$voice.Speak($speechText)
}
finally {
    $stream.Close()
}

Write-Output "Created synthetic spoken WAV: $outputPath"
