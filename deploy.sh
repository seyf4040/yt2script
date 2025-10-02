#!/bin/bash

# YouTube Transcription Tool - Quick Deploy Script
# This script helps deploy the application to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}YouTube Transcription Tool - Deployment Script${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Prompt for configuration
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter deployment region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

read -p "Enter OpenAI API Key: " OPENAI_KEY
read -sp "Enter App Password (for authentication): " APP_PASSWORD
echo

read -p "Enter service name (default: youtube-transcription): " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-youtube-transcription}

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo

read -p "Continue with deployment? (y/n): " CONFIRM
if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set project
echo -e "\n${GREEN}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${GREEN}Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build image
echo -e "\n${GREEN}Building Docker image...${NC}"
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Configure Docker for GCP
echo -e "\n${GREEN}Configuring Docker authentication...${NC}"
gcloud auth configure-docker

# Push image
echo -e "\n${GREEN}Pushing image to Google Container Registry...${NC}"
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo -e "\n${GREEN}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8501 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_KEY,APP_PASSWORD=$APP_PASSWORD,API_URL=http://localhost:8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 1 \
  --min-instances 0

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "Your application is available at:"
echo -e "${GREEN}$SERVICE_URL${NC}"
echo -e "\nUse the following password to access: ${YELLOW}$APP_PASSWORD${NC}"
echo -e "\n${YELLOW}Important:${NC} Store your password securely!"