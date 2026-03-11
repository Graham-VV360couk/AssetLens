# AssetLens - Run Rightmove + SpareRoom scrapers in parallel with live log tail
# Usage: .\scripts\run_rental_scrapers.ps1
# Run from: C:\xampp\htdocs\AssetLens

$DB   = "postgresql://postgres:qAR4w5va0tQXif9DsuvKvZmLn6b9811l9IATXMclHihrNCw4q3t2p29HEjC3Cg2w@159.69.153.234:5432/assetlens"
$Root = "C:\xampp\htdocs\AssetLens"
$RmLog    = "$Root\logs\rightmove_scrape.log"
$RmErrLog = "$Root\logs\rightmove_scrape_stdout.log"
$SrLog    = "$Root\logs\spareroom_scrape.log"
$SrErrLog = "$Root\logs\spareroom_scrape_stdout.log"

# Clear old logs (skip if locked by another process)
foreach ($f in @($RmLog, $RmErrLog, $SrLog, $SrErrLog)) {
    try { "" | Set-Content $f -ErrorAction Stop } catch { Write-Host "Note: could not clear $f (in use)" -ForegroundColor DarkGray }
}

Write-Host "Starting Rightmove and SpareRoom scrapers in parallel..." -ForegroundColor Green
Write-Host "(Ctrl+C to stop watching - scrapers keep running in background)" -ForegroundColor DarkGray
Write-Host ""

$env:DATABASE_URL    = $DB
$env:PYTHONPATH      = $Root
$env:PYTHONUNBUFFERED = "1"

$rmProc = Start-Process -FilePath "python" `
    -ArgumentList @("-u", "-m", "backend.scrapers.rightmove_rental_scraper", "--districts-from-db", "--pages", "999") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $RmErrLog `
    -RedirectStandardError $RmLog `
    -PassThru -NoNewWindow

$srProc = Start-Process -FilePath "python" `
    -ArgumentList @("-u", "-m", "backend.scrapers.rental_scraper", "--districts-from-db", "--pages", "999") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $SrErrLog `
    -RedirectStandardError $SrLog `
    -PassThru -NoNewWindow

Write-Host "Rightmove PID: $($rmProc.Id)   SpareRoom PID: $($srProc.Id)" -ForegroundColor DarkGray
Write-Host ""

# Tail both logs in this window, colour-coded
$rmPos = 0
$srPos = 0

while (-not $rmProc.HasExited -or -not $srProc.HasExited) {
    $rmLines = Get-Content $RmLog -ErrorAction SilentlyContinue
    if ($rmLines -and $rmLines.Count -gt $rmPos) {
        foreach ($line in $rmLines[$rmPos..($rmLines.Count - 1)]) {
            if ($line.Trim()) { Write-Host "[RM] $line" -ForegroundColor Cyan }
        }
        $rmPos = $rmLines.Count
    }

    $srLines = Get-Content $SrLog -ErrorAction SilentlyContinue
    if ($srLines -and $srLines.Count -gt $srPos) {
        foreach ($line in $srLines[$srPos..($srLines.Count - 1)]) {
            if ($line.Trim()) { Write-Host "[SR] $line" -ForegroundColor Yellow }
        }
        $srPos = $srLines.Count
    }

    Start-Sleep -Milliseconds 500
}

# Flush final lines after exit
Start-Sleep -Seconds 1
$rmLines = Get-Content $RmLog -ErrorAction SilentlyContinue
if ($rmLines -and $rmLines.Count -gt $rmPos) {
    foreach ($line in $rmLines[$rmPos..($rmLines.Count - 1)]) {
        if ($line.Trim()) { Write-Host "[RM] $line" -ForegroundColor Cyan }
    }
}
$srLines = Get-Content $SrLog -ErrorAction SilentlyContinue
if ($srLines -and $srLines.Count -gt $srPos) {
    foreach ($line in $srLines[$srPos..($srLines.Count - 1)]) {
        if ($line.Trim()) { Write-Host "[SR] $line" -ForegroundColor Yellow }
    }
}

# Show errors if any
$rmErr = Get-Content $RmErrLog -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }
if ($rmErr) { Write-Host "`n[RM ERRORS]" -ForegroundColor Red; $rmErr | ForEach-Object { Write-Host $_ -ForegroundColor Red } }
$srErr = Get-Content $SrErrLog -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }
if ($srErr) { Write-Host "`n[SR ERRORS]" -ForegroundColor Red; $srErr | ForEach-Object { Write-Host $_ -ForegroundColor Red } }

Write-Host "`n=== Both scrapers complete ===" -ForegroundColor Green
