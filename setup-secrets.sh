#!/bin/bash

# SpeakRight — environment variable checklist for Railway
#
# Railway uses environment variables set directly in the dashboard,
# not a secret manager. This script just prints which variables
# need to be configured.
#
# Dashboard: https://railway.app → your project → service → Variables

VARS=(
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_DEFAULT_REGION"
    "S3_BUCKET_NAME"
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_JWT_SECRET"
    "SUPABASE_SERVICE_ROLE_KEY"
    "GEMINI_API_KEY"
    "LLM_PROVIDER"
    "LLM_MODEL"
    "ATTENDEE_API_KEY"
    "ATTENDEE_WEBHOOK_SECRET"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "GOOGLE_REDIRECT_URI"
    "BASE_URL"
    "FRONTEND_URL"
    "OAUTH_STATE_SECRET"
    "ALLOWED_ORIGINS"
)

ENV_FILE="python/.env"
MISSING=()
SET=()

for var in "${VARS[@]}"; do
    val=$(grep -E "^${var}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
    if [ -z "$val" ]; then
        MISSING+=("$var")
    else
        SET+=("$var")
    fi
done

echo "=== Environment Variable Status ==="
echo ""
for var in "${SET[@]}"; do
    echo "  ✓ $var"
done
for var in "${MISSING[@]}"; do
    echo "  ✗ $var  ← not set"
done

echo ""
if [ ${#MISSING[@]} -eq 0 ]; then
    echo "All variables set. Copy them to the Railway dashboard."
else
    echo "${#MISSING[@]} variable(s) missing. Set them in python/.env"
    echo "then add them to Railway dashboard → Variables."
fi
