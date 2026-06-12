# Automated deployment script for Carbon Account Agent
# Project: hackathon-499200

$ProjectID = "hackathon-499200"
$Region = "us-central1"

# Resolve gcloud command/executable path
$gcloud = "gcloud"
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    $localPath = "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    $systemPath = "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    if (Test-Path $localPath) {
        $gcloud = $localPath
    } elseif (Test-Path $systemPath) {
        $gcloud = $systemPath
    } else {
        Write-Host "Warning: gcloud executable not found. Script will attempt to call 'gcloud' globally." -ForegroundColor Yellow
    }
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Deploying Carbon Account Agent to Google Cloud" -ForegroundColor Cyan
Write-Host " Project: $ProjectID" -ForegroundColor Cyan
Write-Host " Region: $Region" -ForegroundColor Cyan
Write-Host " Using gcloud binary at: $gcloud" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Set the active project
Write-Host "`n[1/4] Setting active gcloud project..." -ForegroundColor Yellow
& $gcloud config set project $ProjectID
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error setting project. Please verify you are logged in using 'gcloud auth login'." -ForegroundColor Red
    exit 1
}

# 2. Enable services
Write-Host "`n[2/4] Enabling Google Cloud services..." -ForegroundColor Yellow
& $gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error enabling APIs." -ForegroundColor Red
    exit 1
}

# 3. Build & Deploy Backend
Write-Host "`n[3/4] Building and deploying Backend (FastAPI)..." -ForegroundColor Yellow
& $gcloud builds submit --tag gcr.io/$ProjectID/carbon-backend ./backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend container build failed." -ForegroundColor Red
    exit 1
}

# Deploy to Cloud Run using SQLite fallback for fast demonstration
# (To use Postgres instead, append database env vars and add Cloud SQL flags)
Write-Host "Deploying Backend container to Cloud Run..." -ForegroundColor Yellow
$BackendURL = & $gcloud run deploy carbon-backend `
  --image gcr.io/$ProjectID/carbon-backend `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --set-env-vars="ENVIRONMENT=production,GEMINI_API_KEY=your_gemini_api_key_here" `
  --format="value(status.url)"

if ($LASTEXITCODE -ne 0 -or -not $BackendURL) {
    Write-Host "Backend deployment to Cloud Run failed." -ForegroundColor Red
    exit 1
}

$BackendURL = $BackendURL.Trim()
Write-Host "Backend successfully deployed to: $BackendURL" -ForegroundColor Green

# 4. Build & Deploy Frontend
Write-Host "`n[4/4] Building and deploying Frontend (React + Vite)..." -ForegroundColor Yellow
& $gcloud builds submit `
  --config=cloudbuild.yaml `
  --substitutions="_VITE_API_URL=$BackendURL" `
  .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend container build failed." -ForegroundColor Red
    exit 1
}

Write-Host "Deploying Frontend container to Cloud Run..." -ForegroundColor Yellow
$FrontendURL = & $gcloud run deploy carbon-frontend `
  --image gcr.io/$ProjectID/carbon-frontend `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --format="value(status.url)"

if ($LASTEXITCODE -ne 0 -or -not $FrontendURL) {
    Write-Host "Frontend deployment to Cloud Run failed." -ForegroundColor Red
    exit 1
}

$FrontendURL = $FrontendURL.Trim()
Write-Host "`n==============================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host " Backend API:  $BackendURL" -ForegroundColor Green
Write-Host " Frontend App: $FrontendURL" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Note: Don't forget to update your GEMINI_API_KEY env var in the Backend Cloud Run service if you want to use the LLM features." -ForegroundColor Yellow
