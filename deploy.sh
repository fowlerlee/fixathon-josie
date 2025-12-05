#!/bin/bash
set -e

# Configuration
SERVICE_NAME="norrsken-app"
REGION="us-central1"

# 1. Ensure a project is selected
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project selected."
    echo "Run 'gcloud config set project YOUR_PROJECT_ID' first."
    exit 1
fi

echo "Deploying to project: $PROJECT_ID"

# 2. Enable necessary APIs
echo "Enabling necessary APIs (Cloud Run, Vision, Vertex AI, Artifact Registry)..."
gcloud services enable run.googleapis.com \
    vision.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com

# 3. Deploy from source
# This builds the container using Cloud Build and deploys it to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT=$PROJECT_ID,VERTEX_LOCATION=$REGION

echo "Deployment complete!"
