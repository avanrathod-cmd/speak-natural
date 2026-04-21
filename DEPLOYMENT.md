# SpeakRight — Deployment Guide

## Production (Railway)

The backend deploys automatically on every push to `master` via
Railway's GitHub integration. The `python/railway.toml` config
points Railway at the Python Dockerfile.

### Manual deploy via CLI

```bash
# Install Railway CLI if needed
npm install -g @railway/cli

# Login
railway login

# Deploy from the python/ directory
cd python && railway up
```

### Environment variables

Set these in the Railway dashboard under your service → Variables:

```
# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=ap-south-1
S3_BUCKET_NAME=speach-analyzer

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_SERVICE_ROLE_KEY=

# LLM
GEMINI_API_KEY=
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash

# Attendee.dev
ATTENDEE_API_KEY=
ATTENDEE_WEBHOOK_SECRET=

# Google OAuth (for calendar linking)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://<your-railway-domain>/attendee/auth/google/callback

# App URLs
BASE_URL=https://<your-railway-domain>
FRONTEND_URL=https://<your-frontend-domain>
OAUTH_STATE_SECRET=

# CORS
ALLOWED_ORIGINS=https://<your-frontend-domain>
```

### View logs

```bash
railway logs
```

---

## Local Development + Webhook Testing

Attendee webhooks require a publicly reachable URL. Use the
included `cloudflared` binary to tunnel localhost to the internet.

### 1. Start the backend

```bash
cd python
uv run uvicorn api.main:app --reload --port 8000
```

### 2. Start the cloudflared tunnel (separate terminal)

```bash
# From the project root
./cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a public URL like:
```
https://xyz-something.trycloudflare.com
```

### 3. Point Attendee at your local server

In `python/.env`, set:
```
BASE_URL=https://xyz-something.trycloudflare.com
```

Then restart the backend (`uv run uvicorn ...`). The webhook
handler at `/attendee/webhook` is now reachable from Attendee.

### 4. Watch logs

With `--reload` on, logs stream directly to the terminal where
you started uvicorn. Look for:

```
# Bot scheduled successfully:
INFO  Scheduled bot <id> for event '<name>'

# Webhook received but no supported meeting found:
INFO  calendar.events_update for <id> — no new Google Meets to schedule

# Recording ingested:
INFO  Starting analysis for bot <id> (call <id>)
INFO  Finished processing call <id>
```

### Notes

- The cloudflared URL changes every time you restart the tunnel.
  Every time it changes, you need to update two things:
  1. `BASE_URL` in `python/.env` (restart the backend after)
  2. The webhook URL in **Attendee dashboard → Settings → Webhooks**
     — change it to `https://<new-url>/attendee/webhook`

  The Attendee dashboard webhook covers `calendar.events_update`
  (new meetings → bot scheduling). Per-bot `bot.state_change`
  webhooks are set at scheduling time, so bots created after the
  URL update will call the correct endpoint automatically.
