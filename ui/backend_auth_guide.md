# Authentication Guide - Supabase Integration

## Overview

SpeakRight uses **Supabase for authentication** with a frontend/backend split architecture:

- **Frontend**: Handles user authentication (signup/signin) with Supabase JS library
- **Backend**: Verifies JWT tokens and enforces access control

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  (React/Next.js/etc + Supabase JS)                          │
│                                                              │
│  1. User signs in with Google via Supabase                  │
│  2. Supabase returns JWT access token                       │
│  3. Frontend stores token (memory/localStorage)             │
│  4. Frontend sends token with every API request             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP Request
                        │ Authorization: Bearer <jwt_token>
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                              │
│  1. Extract JWT from Authorization header                   │
│  2. Verify token with SUPABASE_JWT_SECRET                   │
│  3. Extract user_id from token payload                      │
│  4. Check user owns the requested resource                  │
│  5. Process request and return response                     │
└──────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Supabase Configuration

#### Get Supabase Credentials

1. Create a project at [supabase.com](https://supabase.com)
2. Go to Project Settings → API
3. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGc...` (public key for frontend)
   - **JWT Secret**: Found in Project Settings → API → JWT Settings

#### Enable Google OAuth

1. Go to Authentication → Providers
2. Enable Google provider
3. Add OAuth client ID and secret from Google Cloud Console

### 2. Backend Configuration

Add to `.env` file:

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-super-secret-jwt-secret-here
```

**Important**: The `SUPABASE_JWT_SECRET` is different from the anon key. It's used to verify tokens server-side.

### 3. Install Dependencies

```bash
uv sync  # Installs supabase and pyjwt
```

## Frontend Integration

### Minimal Setup (For Another Claude Session)

Frontend uses Supabase JS to handle authentication. Backend only needs to **verify tokens**.

#### Frontend Authentication Flow

```javascript
// 1. Initialize Supabase client (frontend)
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://your-project.supabase.co',
  'your-anon-key'
)

// 2. Sign in with Google
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})

// 3. Get session and access token
const { data: { session } } = await supabase.auth.getSession()
const accessToken = session?.access_token

// 4. Send token with API requests
const response = await fetch('http://localhost:8000/upload-audio', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
})
```

**That's it!** The backend handles token verification automatically.

## Backend API Usage

### Authentication Flow

All protected endpoints require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <supabase_jwt_token>
```

### Protected Endpoints

All coaching-related endpoints require authentication:

- `POST /upload-audio` - Upload audio
- `GET /coaching/{id}/status` - Get status
- `GET /coaching/{id}/metrics` - Get metrics
- `GET /coaching/{id}/metrics/detailed` - Get detailed metrics
- `GET /coaching/{id}/feedback` - Get feedback
- `GET /coaching/{id}/visualizations/{type}` - Get visualizations
- `GET /coaching/{id}/download` - Download results
- `DELETE /coaching/{id}` - Delete session
- `GET /sessions` - List user's sessions

### Public Endpoints

- `GET /` - Root
- `GET /health` - Health check
- `POST /auth/signup` - Mock signup (deprecated, use Supabase)

### Verify Authentication

Test endpoint to check if token is valid:

```bash
GET /auth/verify
Authorization: Bearer <token>
```

Response:
```json
{
  "authenticated": true,
  "user_id": "uuid-from-supabase",
  "email": "user@example.com",
  "role": "authenticated"
}
```

## Example Usage

### With cURL

```bash
# 1. Get token from frontend (Supabase session)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Verify token works
curl -X GET "http://localhost:8000/auth/verify" \
  -H "Authorization: Bearer $TOKEN"

# 3. Upload audio
curl -X POST "http://localhost:8000/upload-audio" \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio_file=@speech.wav"

# 4. Get results
curl -X GET "http://localhost:8000/coaching/{coaching_id}/metrics" \
  -H "Authorization: Bearer $TOKEN"
```

### With Python

```python
import requests

# Token from Supabase frontend
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

headers = {
    "Authorization": f"Bearer {token}"
}

# Upload audio
with open("speech.wav", "rb") as f:
    files = {"audio_file": f}
    response = requests.post(
        "http://localhost:8000/upload-audio",
        headers=headers,
        files=files
    )

coaching_id = response.json()["coaching_id"]

# Get metrics
metrics = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/metrics",
    headers=headers
).json()
```

### With JavaScript/TypeScript

```typescript
// Get token from Supabase session
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

if (!token) {
  // Redirect to login
  return
}

// Upload audio
const formData = new FormData()
formData.append('audio_file', audioFile)

const response = await fetch('http://localhost:8000/upload-audio', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})

const { coaching_id } = await response.json()

// Get metrics
const metricsResponse = await fetch(
  `http://localhost:8000/coaching/${coaching_id}/metrics`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
)

const metrics = await metricsResponse.json()
```

## Access Control

### User Ownership

All coaching sessions are tied to the authenticated user:

1. When uploading audio, `user_id` is extracted from JWT token
2. Session metadata stores `user_id`
3. All subsequent requests verify the user owns the session

### Authorization Checks

Every protected endpoint performs these checks:

```python
# 1. Verify token is valid
user = get_current_user(authorization_header)

# 2. Load session metadata
metadata = load_session_metadata(coaching_id)

# 3. Verify ownership
if metadata["user_id"] != user["user_id"]:
    raise HTTPException(403, "Access denied")

# 4. Process request
```

### Error Responses

**401 Unauthorized**: Token is missing or invalid
```json
{
  "detail": "Missing authorization header"
}
```

**403 Forbidden**: User doesn't own the resource
```json
{
  "detail": "Access denied: not your coaching session"
}
```

## JWT Token Structure

Supabase JWT tokens contain:

```json
{
  "aud": "authenticated",
  "exp": 1234567890,
  "sub": "user-uuid-here",
  "email": "user@example.com",
  "role": "authenticated",
  "app_metadata": {
    "provider": "google",
    "providers": ["google"]
  },
  "user_metadata": {
    "avatar_url": "...",
    "full_name": "User Name"
  }
}
```

Backend extracts:
- `sub`: User ID (primary identifier)
- `email`: User email
- `exp`: Token expiration
- `role`: User role

## Security Considerations

### Backend

✅ **Token Verification**: All tokens verified with JWT secret
✅ **Expiration Check**: Expired tokens rejected
✅ **Ownership Verification**: Users can only access their own sessions
✅ **HTTPS Only**: Use HTTPS in production

### Frontend

✅ **Token Storage**: Store in memory or secure storage (not localStorage in production)
✅ **Token Refresh**: Handle token expiration with Supabase refresh
✅ **Logout**: Clear tokens on logout

## Testing Authentication

### Local Development

1. Start backend:
```bash
uv run python -m api.main --reload
```

2. Test without auth (should fail):
```bash
curl -X GET "http://localhost:8000/sessions"
# Returns: 401 Unauthorized
```

3. Test with mock token (for development only):
```python
# Generate test token
import jwt
from datetime import datetime, timedelta

payload = {
    "sub": "test-user-123",
    "email": "test@example.com",
    "role": "authenticated",
    "aud": "authenticated",
    "exp": datetime.now() + timedelta(hours=1)
}

token = jwt.encode(payload, "your-jwt-secret", algorithm="HS256")
print(token)
```

4. Test with real token from frontend

## Troubleshooting

### "Invalid token" error

**Problem**: Backend can't verify token

**Solutions**:
- Check `SUPABASE_JWT_SECRET` matches your project
- Verify token format: `Bearer <token>`
- Check token hasn't expired
- Ensure token is from same Supabase project

### "Access denied" error

**Problem**: User doesn't own the resource

**Solutions**:
- Check coaching_id is correct
- Verify user_id in token matches session owner
- Ensure session was created by this user

### "Missing authorization header"

**Problem**: No token sent with request

**Solutions**:
- Add `Authorization: Bearer <token>` header
- Check frontend is sending token
- Verify Supabase session is active

## Migration from Mock Auth

The old mock `/auth/signup` endpoint is deprecated. To migrate:

### Old (Mock)
```javascript
// Don't use this
fetch('/auth/signup', {
  method: 'POST',
  body: JSON.stringify({ email, password })
})
```

### New (Supabase)
```javascript
// Use Supabase instead
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})
```

## Future Enhancements

Planned features:

1. **Role-Based Access**: Admin users, premium features
2. **Team Sharing**: Share sessions with team members
3. **API Keys**: Alternative authentication for integrations
4. **Rate Limiting**: Per-user rate limits
5. **Session Management**: View active sessions, force logout

## Summary for Claude Code Sessions

**If you're implementing the frontend:**
- Use `@supabase/supabase-js` for auth
- Sign in with Google OAuth
- Get `session.access_token` from Supabase
- Send token as `Authorization: Bearer <token>`
- Backend handles everything else

**If you're working on the backend:**
- Authentication is already implemented in `api/auth.py`
- All protected endpoints use `Depends(get_current_user)`
- Tokens are verified automatically
- User ID is in `user["user_id"]`
- Sessions are automatically linked to users

**Configuration needed:**
```bash
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...
```

That's it! Authentication is centralized and consistent across all endpoints.
