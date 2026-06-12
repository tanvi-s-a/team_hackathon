#!/bin/bash
# Automated deployment script for Carbon Account Agent
# Project: hackathon-499200

PROJECT_ID="hackathon-499200"
REGION="us-central1"

echo "=============================================="
echo " Deploying Carbon Account Agent to Google Cloud"
echo " Project: $PROJECT_ID"
echo " Region: $REGION"
echo "=============================================="

# 1. Set the active project
echo -e "\n[1/4] Setting active gcloud project..."
gcloud config set project $PROJECT_ID
if [ $? -ne 0 ]; then
    echo "Error setting project. Please verify you are logged in using 'gcloud auth login'."
    exit 1
fi

# 2. Enable services
echo -e "\n[2/4] Enabling Google Cloud services..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
if [ $? -ne 0 ]; then
    echo "Error enabling APIs."
    exit 1
fi

# 3. Build & Deploy Backend
echo -e "\n[3/4] Building and deploying Backend (FastAPI)..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/carbon-backend ./backend
if [ $? -ne 0 ]; then
    echo "Backend container build failed."
    exit 1
fi

# Deploy to Cloud Run using SQLite fallback for fast demonstration
BackendURL=$(gcloud run deploy carbon-backend \
  --image gcr.io/$PROJECT_ID/carbon-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,GEMINI_API_KEY=your_gemini_api_key_here" \
  --format="value(status.url)")

if [ $? -ne 0 ] || [ -z "$BackendURL" ]; then
    echo "Backend deployment to Cloud Run failed."
    exit 1
fi

BackendURL=$(echo "$BackendURL" | tr -d '\r\n[:space:]')
echo "Backend successfully deployed to: $BackendURL"

# 4. Build & Deploy Frontend
echo -e "\n[4/4] Building and deploying Frontend (React + Vite)..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions="_VITE_API_URL=$BackendURL" \
  .

if [ $? -ne 0 ]; then
    echo "Frontend container build failed."
    exit 1
fi

FrontendURL=$(gcloud run deploy carbon-frontend \
  --image gcr.io/$PROJECT_ID/carbon-frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --format="value(status.url)")

if [ $? -ne 0 ] || [ -z "$FrontendURL" ]; then
    echo "Frontend deployment to Cloud Run failed."
    exit 1
fi

FrontendURL=$(echo "$FrontendURL" | tr -d '\r\n[:space:]')
echo "=============================================="
echo " Deployment Complete!"
echo " Backend API:  $BackendURL"
echo " Frontend App: $FrontendURL"
echo "=============================================="
echo "Note: Don't forget to update your GEMINI_API_KEY env var in the Backend Cloud Run service if you want to use the LLM features."
