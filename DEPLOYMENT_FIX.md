# Backend Deployment Fix - Supabase Database Integration

## What Happened?

The backend deployment failed because we just added **Supabase database integration**, which requires 2 new environment variables that weren't in Google Cloud Secret Manager:

1. `SUPABASE_SERVICE_ROLE_KEY` - Admin access to Supabase database
2. `DATABASE_URL` - PostgreSQL connection string

### Why UI Succeeded but Backend Failed?

**UI (Frontend)** ✅
- Only needs `SUPABASE_URL` and `SUPABASE_ANON_KEY` (public keys)
- Connects to Supabase Auth directly from the browser
- No database access needed
- Already had all required secrets

**Backend (Python API)** ❌
- Now requires admin database access
- Needs `SUPABASE_SERVICE_ROLE_KEY` to bypass Row Level Security
- Needs `DATABASE_URL` to connect to PostgreSQL
- Missing these 2 new secrets → deployment failed

---

## Fix: Add Missing Secrets

### Option 1: Automatic (Recommended)

Run the helper script that reads from your local `.env` file:

```bash
# Set your project ID
export GCP_PROJECT_ID=big-website-445809

# Add the missing secrets
./add-secrets.sh
```

This script will:
- Read `SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` from `python/.env`
- Create/update the secrets in Google Cloud Secret Manager
- Verify everything is ready for deployment

### Option 2: Manual

Add secrets one by one:

```bash
# Set project
export GCP_PROJECT_ID=big-website-445809

# Add service role key
echo -n 'sb_secret_qVCSZe4rrShftDWPOkcbOA_ogBvlKwA' | \
  gcloud secrets create supabase-service-role-key --data-file=-

# Add database URL (note: password is URL-encoded)
echo -n 'postgresql://postgres:lambdakigpt%4012@db.zdyjozeuordbzvxfpecr.supabase.co:5432/postgres' | \
  gcloud secrets create database-url --data-file=-
```

---

## Deploy

### Deploy Backend Only (Recommended for now)

```bash
./deploy.sh --backend-only
```

This will:
- Build and deploy only the Python backend
- Skip the UI deployment (since it's already working)
- Use the new database secrets

### Deploy Both Backend and UI

```bash
./deploy.sh
```

### Deploy UI Only

```bash
./deploy.sh --ui-only
```

### Help

```bash
./deploy.sh --help
```

---

## What Was Updated?

### 1. `python/cloudbuild.yaml`
**Added** 2 new secrets to the `--set-secrets` argument:
```yaml
SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,
DATABASE_URL=database-url:latest
```

### 2. `deploy.sh`
- ✅ Added `--backend-only` and `--ui-only` flags
- ✅ Updated secrets check to include new Supabase secrets
- ✅ Made secrets check conditional (only for backend deployment)
- ✅ Added help menu with `--help`

### 3. `add-secrets.sh` (New)
- Helper script to automatically add secrets from `.env` file
- Creates or updates secrets in Google Cloud

---

## Verification

After adding secrets, verify they exist:

```bash
gcloud secrets describe supabase-service-role-key
gcloud secrets describe database-url
```

List all secrets:

```bash
gcloud secrets list | grep supabase
```

---

## Step-by-Step Fix

```bash
# 1. Set project ID
export GCP_PROJECT_ID=big-website-445809

# 2. Add missing secrets
./add-secrets.sh

# 3. Verify secrets were added
gcloud secrets list | grep -E "(supabase|database)"

# 4. Deploy backend only
./deploy.sh --backend-only

# 5. Verify deployment
gcloud run services describe speakright-api --region=asia-south1
```

---

## Updated Deployment Commands

### Full Deployment (Backend + UI)
```bash
export GCP_PROJECT_ID=big-website-445809
./deploy.sh
```

### Backend Only
```bash
export GCP_PROJECT_ID=big-website-445809
./deploy.sh --backend-only
```

### UI Only
```bash
export GCP_PROJECT_ID=big-website-445809
./deploy.sh --ui-only
```

---

## Troubleshooting

### "Permission denied" on scripts
```bash
chmod +x add-secrets.sh deploy.sh
```

### Secrets already exist
The `add-secrets.sh` script will **update** existing secrets with new versions, so it's safe to run multiple times.

### Wrong region in error
The error shows `asia-south1` but the deploy script defaults to `us-central1`. Set the region:

```bash
export GCP_REGION=asia-south1
./deploy.sh --backend-only
```

### View Cloud Run logs
```bash
gcloud run logs tail speakright-api --region=asia-south1
```

---

## Summary

**Problem**: Backend deployment failed due to missing Supabase database secrets
**Cause**: Just added database integration that requires 2 new environment variables
**Solution**: Add secrets with `./add-secrets.sh`, then deploy with `./deploy.sh --backend-only`

The UI deployment is fine and doesn't need these secrets!

---

**Ready to fix? Run:**

```bash
export GCP_PROJECT_ID=big-website-445809
export GCP_REGION=asia-south1
./add-secrets.sh
./deploy.sh --backend-only
```
