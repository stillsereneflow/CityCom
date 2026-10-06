# render_slides.ps1 — export every slide of the deck to PNG via PowerPoint COM.
# Usage: pwsh -File render_slides.ps1 [-Pptx <path>] [-OutDir <dir>]
param(
    [string]$Pptx = (Join-Path $PSScriptRoot '..\03_答辩PPT.pptx'),
    [string]$OutDir = (Join-Path $PSScriptRoot 'render'),
    [int]$Width = 1600,
    [int]$Height = 900
)

$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path -LiteralPath $Pptx).Path
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path

$ppt = New-Object -ComObject PowerPoint.Application
try {
    # ReadOnly = msoTrue (-1), Untitled = msoFalse (0), WithWindow = msoFalse (0)
    $pres = $ppt.Presentations.Open($Pptx, -1, 0, 0)
    $n = $pres.Slides.Count
    Write-Output "slides: $n"
    for ($i = 1; $i -le $n; $i++) {
        $file = Join-Path $OutDir ("slide{0:d2}.png" -f $i)
        $pres.Slides($i).Export($file, 'PNG', $Width, $Height)
        Write-Output ("exported {0}" -f $file)
    }
    $pres.Close()
}
finally {
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}
