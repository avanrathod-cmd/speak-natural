#!/bin/bash

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"

echo -e "${BLUE}=== SpeakRight Google Cloud Deployment ===${NC}\n"

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID environment variable not set${NC}"
    echo "Please set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install it with: brew install --cask google-cloud-sdk"
    exit 1
fi

# Verify gcloud authentication
echo -e "${BLUE}Verifying authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi

# Set project
echo -e "${BLUE}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

# Enable required APIs
echo -e "\n${BLUE}Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable containerregistry.googleapis.com

echo -e "\n${GREEN}✓ APIs enabled${NC}"

# Check if secrets exist
echo -e "\n${BLUE}Checking secrets...${NC}"
REQUIRED_SECRETS=(
    "aws-access-key"
    "aws-secret-key"
    "anthropic-api-key"
    "openai-api-key"
    "elevenlabs-api-key"
    "supabase-url"
    "supabase-anon-key"
    "supabase-jwt-secret"
)

MISSING_SECRETS=()
for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe "$secret" &> /dev/null; then
        MISSING_SECRETS+=("$secret")
    fi
done

if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
    echo -e "${RED}Missing secrets: ${MISSING_SECRETS[*]}${NC}"
    echo -e "\nCreate them with:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  echo -n 'YOUR_VALUE' | gcloud secrets create $secret --data-file=-"
    done
    exit 1
fi

echo -e "${GREEN}✓ All required secrets found${NC}"

# Deploy Backend
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Deploying Backend API...${NC}"
echo -e "${BLUE}========================================${NC}\n"

cd python
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions=_REGION="$REGION"

cd ..

# Get backend URL
BACKEND_URL=$(gcloud run services describe speakright-api \
    --region "$REGION" \
    --format='value(status.url)')

echo -e "\n${GREEN}✓ Backend deployed at: ${BACKEND_URL}${NC}"

# Deploy Frontend
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Deploying Frontend...${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check for Supabase secrets (optional)
SUPABASE_URL=""
SUPABASE_KEY=""

if gcloud secrets describe supabase-url &> /dev/null; then
    SUPABASE_URL=$(gcloud secrets versions access latest --secret=supabase-url)
fi

if gcloud secrets describe supabase-anon-key &> /dev/null; then
    SUPABASE_KEY=$(gcloud secrets versions access latest --secret=supabase-anon-key)
fi

cd ui/wireframe
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions=_REGION="$REGION",_API_URL="$BACKEND_URL",_SUPABASE_URL="$SUPABASE_URL",_SUPABASE_ANON_KEY="$SUPABASE_KEY"

cd ../..

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe speakright-frontend \
    --region "$REGION" \
    --format='value(status.url)')

echo -e "\n${GREEN}✓ Frontend deployed at: ${FRONTEND_URL}${NC}"

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"
echo -e "Backend API:  ${BACKEND_URL}"
echo -e "Frontend:     ${FRONTEND_URL}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Visit ${FRONTEND_URL} to test your application"
echo -e "2. Check logs with: gcloud run logs tail speakright-api --region=$REGION"
echo -e "3. Monitor with: gcloud run services describe speakright-api --region=$REGION"
