#!/bin/bash

# SpeakRight — Railway deployment helper
#
# Production deploys automatically on push to master via Railway's
# GitHub integration. Use this script to deploy manually from the CLI.
#
# Usage:
#   ./deploy.sh              # deploy backend
#   ./deploy.sh --help

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: ./deploy.sh"
    echo ""
    echo "Deploys the backend to Railway."
    echo "Requires the Railway CLI: npm install -g @railway/cli"
    echo ""
    echo "For automatic deploys, push to master — Railway deploys on"
    echo "every push via the GitHub integration."
    exit 0
fi

if ! command -v railway &> /dev/null; then
    echo -e "${RED}Railway CLI not found.${NC}"
    echo "Install it with: npm install -g @railway/cli"
    exit 1
fi

echo -e "${BLUE}=== SpeakRight Railway Deployment ===${NC}\n"

echo -e "${BLUE}Deploying backend...${NC}"
cd python && railway up

echo -e "\n${GREEN}✓ Deployed. View logs with: railway logs${NC}"
