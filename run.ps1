# Carbon Account Launch Script

Write-Host "====================================================" -ForegroundColor Green
Write-Host "      LAUNCHING CARBON ACCOUNT WEB APP & AGENT" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

# Check if port 8000 (backend) or 6006 (Phoenix) is already in use to prevent issues
$ports = @(8000, 6006)
foreach ($port in $ports) {
    $portActive = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($portActive) {
        Write-Host "Warning: Port $port is already active. Make sure no other server is running on it." -ForegroundColor Yellow
    }
}

# Launch Backend in a separate window
Write-Host "Launching Backend (FastAPI + Arize Phoenix Agent Tracing)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\tanvi\Hackathons\team_hackathon'; `$env:PYTHONIOENCODING='utf-8'; python -m backend.main"

# Launch Frontend in a separate window
Write-Host "Launching Frontend (Vite + React Dashboard)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\tanvi\Hackathons\team_hackathon\frontend'; npm run dev"

Write-Host "----------------------------------------------------" -ForegroundColor Green
Write-Host "Done! The servers are running in separate terminals." -ForegroundColor Green
Write-Host "API endpoint: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Arize Phoenix Console: http://localhost:6006" -ForegroundColor Magenta
Write-Host "Frontend App: Check the frontend terminal for URL (usually http://localhost:5173)" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Green
