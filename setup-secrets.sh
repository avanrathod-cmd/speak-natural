#!/bin/bash

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Google Cloud Secret Manager Setup ===${NC}\n"

# Check if .env file exists
ENV_FILE="python/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}"
    echo "Please create the .env file with your API keys first."
    exit 1
fi

# Load environment variables from .env
echo -e "${BLUE}Loading credentials from $ENV_FILE...${NC}"
source "$ENV_FILE"

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

echo -e "\n${BLUE}Creating secrets in Google Cloud Secret Manager...${NC}\n"

# Function to create or update a secret
create_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ]; then
        echo -e "${YELLOW}⚠ Skipping $secret_name (value is empty)${NC}"
        return
    fi

    # Check if secret already exists
    if gcloud secrets describe "$secret_name" &> /dev/null; then
        echo -e "${YELLOW}Secret '$secret_name' already exists. Updating...${NC}"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
        echo -e "${GREEN}✓ Updated $secret_name${NC}"
    else
        echo -e "${BLUE}Creating $secret_name...${NC}"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
        echo -e "${GREEN}✓ Created $secret_name${NC}"
    fi
}

# Create all secrets
echo -e "${BLUE}[1/9] AWS Access Key${NC}"
create_secret "aws-access-key" "$AWS_ACCESS_KEY_ID"

echo -e "\n${BLUE}[2/9] AWS Secret Key${NC}"
create_secret "aws-secret-key" "$AWS_SECRET_ACCESS_KEY"

echo -e "\n${BLUE}[3/9] Anthropic API Key${NC}"
create_secret "anthropic-api-key" "$ANTHROPIC_API_KEY"

echo -e "\n${BLUE}[4/9] OpenAI API Key${NC}"
create_secret "openai-api-key" "$OPENAI_API_KEY"

echo -e "\n${BLUE}[5/9] ElevenLabs API Key${NC}"
create_secret "elevenlabs-api-key" "$ELEVENLABS_API_KEY"

echo -e "\n${BLUE}[6/9] ElevenLabs Voice ID${NC}"
create_secret "elevenlabs-voice-id" "$ELEVENLABS_VOICE_ID"

echo -e "\n${BLUE}[7/9] Supabase URL${NC}"
create_secret "supabase-url" "$SUPABASE_URL"

echo -e "\n${BLUE}[8/9] Supabase Anon Key${NC}"
create_secret "supabase-anon-key" "$SUPABASE_ANON_KEY"

echo -e "\n${BLUE}[9/9] Supabase JWT Secret${NC}"
create_secret "supabase-jwt-secret" "$SUPABASE_JWT_SECRET"

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ All secrets created successfully!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}Next steps:${NC}"
echo -e "1. Review secrets: ${BLUE}gcloud secrets list${NC}"
echo -e "2. Deploy application: ${BLUE}./deploy.sh${NC}"
echo -e "\n${YELLOW}Note: Secrets are managed in Google Cloud Secret Manager${NC}"
echo -e "View them at: https://console.cloud.google.com/security/secret-manager"
