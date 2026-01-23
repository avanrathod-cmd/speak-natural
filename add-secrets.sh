#!/bin/bash

# Script to add new Supabase database secrets to Google Cloud Secret Manager

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Adding New Supabase Secrets to Google Cloud ===${NC}\n"

# Check if project ID is set
PROJECT_ID="${GCP_PROJECT_ID:-}"
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    echo "Set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo -e "${BLUE}Project: ${PROJECT_ID}${NC}\n"

# Load values from local .env file
ENV_FILE="python/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: ${ENV_FILE} not found${NC}"
    exit 1
fi

echo -e "${BLUE}Loading secrets from ${ENV_FILE}...${NC}\n"

# Extract values from .env
SERVICE_ROLE_KEY=$(grep "^SUPABASE_SERVICE_ROLE_KEY=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")

# Validate
if [ -z "$SERVICE_ROLE_KEY" ] || [ "$SERVICE_ROLE_KEY" = "YOUR_SERVICE_ROLE_KEY_HERE" ]; then
    echo -e "${RED}Error: SUPABASE_SERVICE_ROLE_KEY not set in ${ENV_FILE}${NC}"
    exit 1
fi

if [ -z "$DATABASE_URL" ] || [ "$DATABASE_URL" = "postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres" ]; then
    echo -e "${RED}Error: DATABASE_URL not set in ${ENV_FILE}${NC}"
    exit 1
fi

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2

    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        echo -e "${YELLOW}Secret '$secret_name' exists, adding new version...${NC}"
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
            --project="$PROJECT_ID" \
            --data-file=-
        echo -e "${GREEN}✓ Updated $secret_name${NC}"
    else
        echo -e "${BLUE}Creating secret '$secret_name'...${NC}"
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --project="$PROJECT_ID" \
            --replication-policy="automatic" \
            --data-file=-
        echo -e "${GREEN}✓ Created $secret_name${NC}"
    fi
}

# Create secrets
echo -e "${BLUE}Creating/updating secrets...${NC}\n"

create_or_update_secret "supabase-service-role-key" "$SERVICE_ROLE_KEY"
create_or_update_secret "database-url" "$DATABASE_URL"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Secrets added successfully!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}Next step: Deploy your backend${NC}"
echo -e "  ./deploy.sh --backend-only\n"
