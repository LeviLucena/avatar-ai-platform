# Starts the API (:8000) and the web app (:5173) in two windows.  Usage:  .\start.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "Creating Python venv and installing dependencies..."
  python -m venv (Join-Path $root "backend\.venv")
  & $py -m pip install -q -r (Join-Path $root "backend\requirements.txt")
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
  Write-Host "Installing frontend dependencies..."
  Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$py' -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Write-Host "API:  http://localhost:8000/docs"
Write-Host "App:  http://localhost:5173   (first start seeds demo data: wait ~15 s)"
Start-Sleep 4
Start-Process "http://localhost:5173"
