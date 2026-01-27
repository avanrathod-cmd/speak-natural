#!/bin/bash

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
FRONTEND_REGION="${GCP_FRONTEND_REGION:-asia-southeast1}"

# Deployment options
DEPLOY_BACKEND=true
DEPLOY_UI=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            DEPLOY_BACKEND=true
            DEPLOY_UI=false
            shift
            ;;
        --ui-only|--frontend-only)
            DEPLOY_BACKEND=false
            DEPLOY_UI=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backend-only        Deploy only the backend API"
            echo "  --ui-only             Deploy only the frontend UI"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  GCP_PROJECT_ID        Google Cloud project ID (required)"
            echo "  GCP_REGION            Backend region (default: us-central1)"
            echo "  GCP_FRONTEND_REGION   Frontend region (default: asia-southeast1)"
            echo ""
            echo "Examples:"
            echo "  ./deploy.sh                    # Deploy both backend and UI"
            echo "  ./deploy.sh --backend-only     # Deploy only backend"
            echo "  ./deploy.sh --ui-only          # Deploy only UI"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=== SpeakRight Google Cloud Deployment ===${NC}\n"

if [ "$DEPLOY_BACKEND" = true ] && [ "$DEPLOY_UI" = true ]; then
    echo -e "${YELLOW}Deploying: Backend + UI${NC}"
    echo -e "${BLUE}Backend region: ${REGION}${NC}"
    echo -e "${BLUE}Frontend region: ${FRONTEND_REGION}${NC}\n"
elif [ "$DEPLOY_BACKEND" = true ]; then
    echo -e "${YELLOW}Deploying: Backend only${NC}"
    echo -e "${BLUE}Backend region: ${REGION}${NC}\n"
else
    echo -e "${YELLOW}Deploying: UI only${NC}"
    echo -e "${BLUE}Frontend region: ${FRONTEND_REGION}${NC}\n"
fi

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

# Check if secrets exist (only for backend deployment)
if [ "$DEPLOY_BACKEND" = true ]; then
    echo -e "\n${BLUE}Checking backend secrets...${NC}"
    REQUIRED_SECRETS=(
        "aws-access-key"
        "aws-secret-key"
        "anthropic-api-key"
        "openai-api-key"
        "elevenlabs-api-key"
        "supabase-url"
        "supabase-anon-key"
        "supabase-jwt-secret"
        "supabase-service-role-key"
        "database-url"
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

    echo -e "${GREEN}✓ All required backend secrets found${NC}"
fi

# Deploy Backend
if [ "$DEPLOY_BACKEND" = true ]; then
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
else
    # Get existing backend URL if available
    if gcloud run services describe speakright-api --region "$REGION" &> /dev/null; then
        BACKEND_URL=$(gcloud run services describe speakright-api \
            --region "$REGION" \
            --format='value(status.url)')
        echo -e "\n${BLUE}Using existing backend URL: ${BACKEND_URL}${NC}"
    else
        BACKEND_URL="<BACKEND_URL_NOT_AVAILABLE>"
        echo -e "\n${YELLOW}Warning: Backend not deployed, frontend will need manual configuration${NC}"
    fi
fi

# Deploy Frontend
if [ "$DEPLOY_UI" = true ]; then
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
    --substitutions=_REGION="$FRONTEND_REGION",_API_URL="$BACKEND_URL",_SUPABASE_URL="$SUPABASE_URL",_SUPABASE_ANON_KEY="$SUPABASE_KEY"

cd ../..

    # Get frontend URL
    FRONTEND_URL=$(gcloud run services describe speakright-frontend \
        --region "$FRONTEND_REGION" \
        --format='value(status.url)')

    echo -e "\n${GREEN}✓ Frontend deployed at: ${FRONTEND_URL}${NC}"
else
    # Get existing frontend URL if available
    if gcloud run services describe speakright-frontend --region "$FRONTEND_REGION" &> /dev/null; then
        FRONTEND_URL=$(gcloud run services describe speakright-frontend \
            --region "$FRONTEND_REGION" \
            --format='value(status.url)')
    else
        FRONTEND_URL="<FRONTEND_URL_NOT_AVAILABLE>"
    fi
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

if [ "$DEPLOY_BACKEND" = true ]; then
    echo -e "Backend API:  ${BACKEND_URL}"
fi

if [ "$DEPLOY_UI" = true ]; then
    echo -e "Frontend:     ${FRONTEND_URL}"
fi

echo -e "\n${BLUE}Next steps:${NC}"

if [ "$DEPLOY_UI" = true ] && [ "$FRONTEND_URL" != "<FRONTEND_URL_NOT_AVAILABLE>" ]; then
    echo -e "1. Visit ${FRONTEND_URL} to test your application"
fi

if [ "$DEPLOY_BACKEND" = true ]; then
    echo -e "2. Check backend logs: gcloud run logs tail speakright-api --region=$REGION"
    echo -e "3. Monitor backend: gcloud run services describe speakright-api --region=$REGION"
fi

if [ "$DEPLOY_UI" = true ]; then
    echo -e "4. Check frontend logs: gcloud run logs tail speakright-frontend --region=$FRONTEND_REGION"
fi
