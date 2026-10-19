# Records the Windows Terminal window as a video, then a GIF, for the README.
# Usage : .\scripts\record-demo.ps1 [-Seconds 20]
# While recording, switch the session's theme from the Ambiance app (Sessions tab)
# or with /ambiance <theme>, then run a failing test and a passing one.
param([int]$Seconds = 20)

$ErrorActionPreference = "Stop"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg is required: winget install Gyan.FFmpeg" }

$window = Get-Process -Name WindowsTerminal | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
if (-not $window) { throw "Open Windows Terminal with a Claude Code session first." }

$out = Join-Path $PSScriptRoot "..\docs"
$video = Join-Path $out "demo.mp4"
Write-Host "Recording '$($window.MainWindowTitle)' for $Seconds s…"
ffmpeg -y -f gdigrab -framerate 30 -t $Seconds -i "title=$($window.MainWindowTitle)" -vf "scale=1280:-2" -c:v libx264 -pix_fmt yuv420p $video

$palette = Join-Path $env:TEMP "ambiance-palette.png"
ffmpeg -y -i $video -vf "fps=15,scale=960:-1:flags=lanczos,palettegen" $palette
ffmpeg -y -i $video -i $palette -lavfi "fps=15,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse" (Join-Path $out "demo.gif")
Write-Host "Done: docs\demo.mp4 and docs\demo.gif"
