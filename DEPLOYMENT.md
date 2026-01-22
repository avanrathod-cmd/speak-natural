# Google Cloud Deployment Guide

This guide covers deploying SpeakRight to Google Cloud using Cloud Run.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Manual Deployment](#manual-deployment)
- [Important Notes](#important-notes)
- [Storage Considerations](#storage-considerations)
- [Monitoring & Debugging](#monitoring--debugging)

## Prerequisites

1. **Google Cloud SDK**: Install the gcloud CLI
   ```bash
   brew install --cask google-cloud-sdk
   ```

2. **Google Cloud Project**: Create a project at https://console.cloud.google.com

3. **Environment Variables**: Have your API keys ready in `python/.env`:
   - AWS credentials (for S3 storage)
   - Anthropic API key
   - OpenAI API key
   - ElevenLabs API key
   - Supabase credentials (URL, Anon Key, JWT Secret)

## Quick Start

**TL;DR - Three Commands to Deploy:**

```bash
export GCP_PROJECT_ID="your-project-id" && gcloud config set project $GCP_PROJECT_ID
./setup-secrets.sh    # One-time: Create secrets from python/.env
./deploy.sh           # Deploy backend and frontend to Cloud Run
```

### 1. Set Up Environment

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"  # or your preferred region

# Set project
gcloud config set project $GCP_PROJECT_ID
```

### 2. Create Secrets

**Option A: Automated Setup (Recommended)**

If you have a `python/.env` file with all your credentials:

```bash
# Run the automated setup script
./setup-secrets.sh
```

This script will read your `.env` file and automatically create/update all secrets in Google Cloud Secret Manager.

**Option B: Manual Setup**

```bash
# Create secrets for sensitive environment variables

# AWS Credentials (for S3 storage)
echo -n "YOUR_AWS_ACCESS_KEY" | gcloud secrets create aws-access-key --data-file=-
echo -n "YOUR_AWS_SECRET_KEY" | gcloud secrets create aws-secret-key --data-file=-

# AI API Keys
echo -n "YOUR_ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "YOUR_ELEVENLABS_KEY" | gcloud secrets create elevenlabs-api-key --data-file=-

# Supabase Authentication (Required)
echo -n "YOUR_SUPABASE_URL" | gcloud secrets create supabase-url --data-file=-
echo -n "YOUR_SUPABASE_ANON_KEY" | gcloud secrets create supabase-anon-key --data-file=-
echo -n "YOUR_SUPABASE_JWT_SECRET" | gcloud secrets create supabase-jwt-secret --data-file=-
```

**Finding Your Credentials:**
- **Supabase**: Project Settings → API
  - URL: Project URL
  - Anon Key: anon/public key
  - JWT Secret: JWT Secret
- **AWS**: IAM Console → Users → Security Credentials
- **AI APIs**: Check respective provider dashboards

### 3. Deploy with Script

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
- Verify authentication
- Enable required APIs
- Check for required secrets
- Deploy backend API
- Deploy frontend with backend URL
- Display deployment URLs

## Manual Deployment

### Backend API

```bash
# Navigate to Python directory
cd python

# Submit build and deploy
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_REGION="us-central1"

# Get backend URL
gcloud run services describe speakright-api \
  --region us-central1 \
  --format='value(status.url)'
```

### Frontend

```bash
# Navigate to frontend directory
cd ui/wireframe

# Get backend URL from previous step
BACKEND_URL="https://speakright-api-XXXXXXXXXX.a.run.app"

# Submit build and deploy
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_REGION="us-central1",_API_URL="$BACKEND_URL"

# Get frontend URL
gcloud run services describe speakright-frontend \
  --region us-central1 \
  --format='value(status.url)'
```

## Important Notes

### Platform Architecture
All Docker images are configured for `linux/amd64` architecture to ensure compatibility with Google Cloud infrastructure. This prevents issues when building on ARM-based machines (M1/M2 Macs).

### CORS Configuration
The backend currently allows all origins (`allow_origins=["*"]`). For production, update this in `python/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",
        "https://speakright-frontend-xyz.a.run.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Storage Considerations

### Ephemeral Storage on Cloud Run

**IMPORTANT**: Cloud Run containers have ephemeral file systems. All files in `/tmp/speak-right` are:
- **Temporary**: Lost when the container scales down or restarts
- **Instance-specific**: Not shared between container instances
- **Limited**: Max 1GB of writable storage

### Current Behavior

1. **Uploaded audio files** → Saved to `/tmp` → Processed → Uploaded to S3
2. **Analysis results** → Saved to `/tmp` → Some uploaded to S3
3. **Session metadata** → Saved to `/tmp` (JSON files) → **NOT uploaded to S3**
4. **Generated segments** → Saved to `/tmp` → Uploaded to S3 on-demand
5. **Cached waveforms** → Saved to `/tmp` → **NOT persisted**

### Implications

- ✅ **Works for**: Single-request processing (upload → process → download)
- ⚠️ **Limited**: Session persistence across container restarts
- ❌ **Fails for**: Long-term session storage, multi-request workflows

### Solutions

**Option 1: Use S3 as Primary Storage** (Recommended for now)
The app already uploads most files to S3. Sessions work as long as:
- Users complete their workflow in one session
- Container doesn't restart mid-processing

**Option 2: Migrate to Google Cloud Storage**
Replace S3 with GCS for better integration:
- Lower latency within Google Cloud
- Better cost for intra-cloud transfers
- Simpler IAM integration

**Option 3: Add Database for Metadata**
Use Cloud SQL or Firestore for session metadata instead of local JSON files.

### Recommended Architecture (Future)

```
User Upload → Cloud Run (Processing) → GCS (Permanent Storage)
                ↓
          Cloud SQL (Metadata)
```

## Monitoring & Debugging

### View Logs

```bash
# Stream backend logs
gcloud run logs tail speakright-api --region=us-central1

# Stream frontend logs
gcloud run logs tail speakright-frontend --region=us-central1
```

### Check Service Status

```bash
# Backend status
gcloud run services describe speakright-api --region=us-central1

# Frontend status
gcloud run services describe speakright-frontend --region=us-central1
```

### Update Services

```bash
# Update backend environment variables
gcloud run services update speakright-api \
  --region=us-central1 \
  --set-env-vars="NEW_VAR=value"

# Update frontend
gcloud run services update speakright-frontend \
  --region=us-central1 \
  --set-env-vars="NEW_VAR=value"
```

### Scale Configuration

```bash
# Update scaling settings
gcloud run services update speakright-api \
  --region=us-central1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --cpu=2 \
  --memory=2Gi
```

## Cost Optimization

1. **Min instances**: Set to 0 to avoid charges when idle
2. **Max instances**: Set limit to control costs (default: 10)
3. **Memory**: Start with 1Gi for backend, 512Mi for frontend
4. **CPU**: Use 1 CPU initially, scale up if needed

### Estimated Costs (us-central1)

- **Idle**: $0/month (min-instances=0)
- **Light usage** (100 requests/day): ~$5-10/month
- **Moderate usage** (1000 requests/day): ~$20-40/month

*Note: Costs vary based on processing time and memory usage*

## Troubleshooting

### Build Fails

```bash
# Check Cloud Build logs
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### Service Not Starting

```bash
# Check service logs
gcloud run logs tail speakright-api --region=us-central1

# Common issues:
# 1. Missing secrets - verify all secrets exist
# 2. Port mismatch - ensure app listens on $PORT (default: 8000)
# 3. Health check fails - verify /health endpoint works
```

### Secrets Not Found

```bash
# List all secrets
gcloud secrets list

# Create missing secret
echo -n "VALUE" | gcloud secrets create SECRET_NAME --data-file=-
```

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use Secret Manager** for all sensitive data
3. **Enable HTTPS** (automatic with Cloud Run)
4. **Configure CORS** properly for production
5. **Add authentication** for sensitive endpoints
6. **Regular updates** to dependencies and base images

## Next Steps

After deployment:
1. Test the application with the provided URLs
2. Set up custom domain (optional)
3. Configure CDN (optional)
4. Set up monitoring alerts
5. Plan for database/storage migration if needed
