# Speech Coach AI - Frontend Setup Guide

## Overview

This is the TypeScript + React frontend for Speech Coach AI, a platform for analyzing and improving American English communication in sales calls.

## Tech Stack

- **React 19** with TypeScript
- **Tailwind CSS** for styling
- **Supabase** for authentication
- **Lucide React** for icons
- Backend API integration (FastAPI)

## Prerequisites

- Node.js 16+ and npm
- Supabase account (for authentication)
- Backend API running (default: http://localhost:8000)

## Setup Instructions

### 1. Install Dependencies

```bash
cd /Users/karma/code/speak-right/ui/wireframe
npm install
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key-here
REACT_APP_API_URL=http://localhost:8000
```

### 3. Set Up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → API**
3. Copy:
   - **Project URL** → `REACT_APP_SUPABASE_URL`
   - **anon/public key** → `REACT_APP_SUPABASE_ANON_KEY`
4. Enable Google OAuth:
   - Go to **Authentication → Providers**
   - Enable Google provider
   - Add OAuth credentials from Google Cloud Console

### 4. Start the Development Server

```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

### 5. Start the Backend API

In a separate terminal:

```bash
cd /Users/karma/code/speak-right/python
python -m api.main --reload
```

Backend will run at [http://localhost:8000](http://localhost:8000)

## Project Structure

```
src/
├── App.tsx                    # Main application component
├── index.tsx                  # Entry point with AuthProvider
├── contexts/
│   └── AuthContext.tsx        # Supabase authentication context
├── services/
│   └── api.ts                 # Backend API service layer
├── types/
│   └── index.ts               # TypeScript type definitions
├── data/
│   └── mockData.ts            # Mock data for features not yet in backend
└── App.css                    # Styles
```

## Features

### ✅ Implemented Features

1. **Authentication**
   - Google OAuth via Supabase
   - JWT token management
   - Protected routes

2. **Upload/Record**
   - File upload for audio analysis
   - Browser-based audio recording
   - Real-time status polling

3. **Analysis View**
   - Overall metrics dashboard
   - Detailed metrics from backend API
   - Waveform visualization (mock data)
   - Interactive transcript (mock data)
   - AI coaching feedback
   - Progress tracker (mock data)

### 🚧 Using Mock Data (Backend Not Ready)

The following features use mock data because the backend APIs don't exist yet:

1. **Interactive Transcript** - Segment-level text with audio playback
2. **Progress Tracker** - Historical improvement data
3. **Waveform Segments** - Color-coded quality visualization

See `API_changes.md` for required backend endpoints.

## Available Scripts

### `npm start`
Runs the app in development mode at [http://localhost:3000](http://localhost:3000)

### `npm test`
Launches the test runner

### `npm run build`
Builds the app for production to the `build` folder

## Backend Integration

### API Endpoints Used

- `POST /upload-audio` - Upload audio file
- `GET /coaching/{id}/status` - Poll processing status
- `GET /coaching/{id}/metrics/detailed` - Get detailed metrics
- `GET /coaching/{id}/feedback` - Get AI coaching (not used yet)
- `GET /coaching/{id}/visualizations/{type}` - Get charts (not used yet)

### Authentication Flow

1. User clicks "Sign in with Google"
2. Supabase handles OAuth redirect
3. Frontend receives JWT access token
4. Token sent in `Authorization: Bearer {token}` header
5. Backend verifies token with Supabase JWT secret

## Mock Data

Mock data is located in `src/data/mockData.ts`:

- `mockTranscriptSegments` - Sample transcript with timing
- `mockProgressData` - Progress tracking data
- `mockWaveformSegments` - Waveform visualization data

These will be replaced with real API calls once backend endpoints are implemented.

## Known Issues

1. **TypeScript version conflict** - Using `--legacy-peer-deps` for Supabase installation
2. **Segment audio playback** - Not implemented (needs backend API)
3. **Progress tracking** - Static mock data (needs database)
4. **Improved audio generation** - Not available yet (needs TTS integration)

## Next Steps

### Frontend
- [ ] Add error boundaries for better error handling
- [ ] Implement audio player components for segment playback
- [ ] Add loading skeletons for better UX
- [ ] Implement downloadable reports
- [ ] Add session history view

### Backend (See API_changes.md)
- [ ] Implement segment-level transcript API
- [ ] Add progress tracker endpoints
- [ ] Generate improved audio segments
- [ ] Add waveform data endpoint
- [ ] Implement practice recording comparison

## Troubleshooting

### "Missing environment variables"
Make sure `.env` file exists with all required variables.

### "Authentication failed"
1. Check Supabase URL and anon key are correct
2. Verify Google OAuth is enabled in Supabase
3. Check redirect URL in Google Cloud Console

### "Upload failed"
1. Ensure backend is running at `REACT_APP_API_URL`
2. Check backend authentication is configured
3. Verify file size is within limits

### "Cannot connect to backend"
1. Start backend: `python -m api.main --reload`
2. Check `REACT_APP_API_URL` matches backend URL
3. Verify CORS is enabled in backend

## Contributing

When adding new features:

1. Add TypeScript types to `src/types/index.ts`
2. Add API methods to `src/services/api.ts`
3. Update mock data in `src/data/mockData.ts` if needed
4. Document new API requirements in `API_changes.md`

## Support

For issues or questions:
- Check backend logs: `/tmp/speak-right.log`
- Review browser console for errors
- Verify environment variables are set
- Check Supabase dashboard for auth issues
