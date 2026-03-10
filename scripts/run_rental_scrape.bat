@echo off
REM ============================================================
REM  AssetLens — Weekly Rental Data Scrape
REM  Run overnight once a week (connect VPN first for fresh IP).
REM
REM  Requirements:
REM    pip install playwright && playwright install chromium
REM ============================================================

cd /d C:\xampp\htdocs\AssetLens

REM Load scraper environment
for /f "tokens=1,2 delims==" %%A in (backend\.env.scraper) do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
)

echo.
echo ============================================================
echo  AssetLens Rental Scraper — %DATE% %TIME%
echo  Connecting to: 159.69.153.234:5432
echo ============================================================
echo.

echo [1/3] Scraping Rightmove (whole-property rents)...
python -m backend.scrapers.rightmove_rental_scraper --districts-from-db --pages 10
if %ERRORLEVEL% NEQ 0 echo WARNING: Rightmove scraper exited with error %ERRORLEVEL%

echo.
echo [2/3] Scraping SpareRoom (HMO room rents)...
python -m backend.scrapers.rental_scraper --districts-from-db --pages 3
if %ERRORLEVEL% NEQ 0 echo WARNING: SpareRoom scraper exited with error %ERRORLEVEL%

echo.
echo [3/3] Triggering re-score on server...
curl -s -X POST https://assetlens.geekybee.net/api/scoring/run
echo.

echo.
echo ============================================================
echo  Done! Check https://assetlens.geekybee.net for results.
echo ============================================================
pause
