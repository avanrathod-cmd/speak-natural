# API Changes Required for Full Frontend Integration

This document outlines the API endpoints that are **NOT yet available** in the backend but are required for full functionality of the Speech Coach AI frontend application.

## Current Status

### ✅ Available APIs (Already Implemented)
- `POST /upload-audio` - Upload audio file
- `GET /coaching/{id}/status` - Get processing status
- `GET /coaching/{id}/metrics` - Get overall metrics
- `GET /coaching/{id}/metrics/detailed` - Get detailed metrics with ratings
- `GET /coaching/{id}/feedback` - Get general coaching feedback
- `GET /coaching/{id}/visualizations/{type}` - Get visualization SVGs
- `GET /coaching/{id}/download` - Download all results as ZIP
- `GET /auth/verify` - Verify authentication token

---

## ❌ Missing APIs (Need Implementation)

### 1. Interactive Transcript with Segment-Level Audio

**Endpoint:** `GET /coaching/{coaching_id}/transcript`

**Purpose:** Provide time-stamped transcript segments with playback URLs for original and improved audio

**Expected Response:**
```json
{
  "coaching_id": "coach_abc123",
  "segments": [
    {
      "segment_id": 1,
      "text": "Hi Sarah, thanks for taking the time today.",
      "start_time": 0.0,
      "end_time": 3.2,
      "original_audio_url": "https://s3.../segment_1_original.wav",
      "improved_audio_url": "https://s3.../segment_1_improved.wav",
      "issue_type": null,
      "issue_description": null,
      "severity": "good",
      "tip": null,
      "metrics": {
        "pace_wpm": 140,
        "pitch_range_hz": 85.2,
        "energy_db": 65.3
      }
    },
    {
      "segment_id": 2,
      "text": "I wanted to walk you through our new analytics platform and show you how it can really transform your team's workflow.",
      "start_time": 3.2,
      "end_time": 9.5,
      "original_audio_url": "https://s3.../segment_2_original.wav",
      "improved_audio_url": "https://s3.../segment_2_improved.wav",
      "issue_type": "too-fast",
      "issue_description": "Too fast (180 wpm) - Add pauses",
      "severity": "warning",
      "tip": "Add a pause after 'platform' and before 'and show you'",
      "metrics": {
        "pace_wpm": 180,
        "pitch_range_hz": 92.1,
        "energy_db": 68.5
      }
    }
  ]
}
```

**Implementation Notes:**
- Split original audio into 5-10 second segments based on natural sentence boundaries
- Use AWS Transcribe word-level timestamps to determine segment boundaries
- Store segment audio files in S3 with predictable naming: `{coaching_id}/segments/segment_{id}_original.wav`
- Generate improved versions using AI-guided SSML with ElevenLabs or similar TTS
- Store improved audio: `{coaching_id}/segments/segment_{id}_improved.wav`
- Return signed S3 URLs for frontend playback
- Include segment-level metrics (pace, pitch, energy) for each segment

**Technical Requirements:**
- Audio segmentation library (pydub or similar)
- SSML generation based on identified issues
- Text-to-speech API integration (ElevenLabs, AWS Polly)
- Prosody adjustment for improved versions

---

### 2. Progress Tracker Data

**Endpoint:** `GET /coaching/progress`

**Purpose:** Track user's improvement over time across all their coaching sessions

**Query Parameters:**
- `user_id` (optional, defaults to authenticated user)
- `timeframe` (optional: `week`, `month`, `all`, defaults to `month`)

**Expected Response:**
```json
{
  "user_id": "user_123",
  "timeframe": "month",
  "current_period": {
    "score_change": 0.8,
    "calls_analyzed": 23,
    "segments_practiced": 127,
    "average_score": 7.2
  },
  "historical_data": [
    {
      "date": "2026-01-01",
      "overall_score": 6.2,
      "pace_rating": "good",
      "pitch_rating": "moderate",
      "energy_rating": "moderate"
    },
    {
      "date": "2026-01-08",
      "overall_score": 6.5,
      "pace_rating": "good",
      "pitch_rating": "good",
      "energy_rating": "moderate"
    },
    {
      "date": "2026-01-15",
      "overall_score": 7.2,
      "pace_rating": "excellent",
      "pitch_rating": "good",
      "energy_rating": "good"
    }
  ],
  "breakdown_by_metric": {
    "pace": {
      "current_avg": 148,
      "target": 145,
      "trend": "improving"
    },
    "pitch_variation": {
      "current_avg": 105.2,
      "target": 100,
      "trend": "stable"
    },
    "energy_level": {
      "current_avg": 67.5,
      "target": 70,
      "trend": "improving"
    }
  },
  "achievements": [
    {
      "title": "First Analysis Complete",
      "earned_at": "2026-01-01"
    },
    {
      "title": "10 Sessions Milestone",
      "earned_at": "2026-01-10"
    }
  ]
}
```

**Implementation Notes:**
- Store session metadata with user_id and timestamp in database
- Calculate aggregated statistics across all user sessions
- Track improvement trends over time
- Provide weekly/monthly comparison data
- Optional: Add gamification elements (achievements, streaks)

**Technical Requirements:**
- Database schema for session history
- Aggregation queries for trend analysis
- Date range filtering logic

---

### 3. Waveform Visualization Data

**Endpoint:** `GET /coaching/{coaching_id}/waveform`

**Purpose:** Provide data for rendering an interactive audio waveform with color-coded quality segments

**Expected Response:**
```json
{
  "coaching_id": "coach_abc123",
  "duration_seconds": 18.5,
  "sample_rate": 44100,
  "waveform_data": {
    "peaks": [0.2, 0.5, 0.8, 0.6, ...],  // Amplitude values at regular intervals
    "sample_interval_ms": 100  // One peak every 100ms
  },
  "quality_segments": [
    {
      "start_time": 0.0,
      "end_time": 3.2,
      "quality": "good",
      "color": "#10b981"
    },
    {
      "start_time": 3.2,
      "end_time": 9.5,
      "quality": "warning",
      "color": "#f59e0b"
    },
    {
      "start_time": 9.5,
      "end_time": 13.0,
      "quality": "warning",
      "color": "#f59e0b"
    },
    {
      "start_time": 13.0,
      "end_time": 18.5,
      "quality": "good",
      "color": "#10b981"
    }
  ]
}
```

**Implementation Notes:**
- Extract waveform peaks from original audio file
- Downsample to ~100ms intervals for web rendering
- Map transcript segments to time ranges
- Assign quality color based on segment severity (good/warning/error)
- Return normalized amplitude values (0.0 to 1.0)

**Technical Requirements:**
- Audio analysis library (librosa, scipy)
- Waveform peak extraction
- Quality mapping from segment analysis

---

### 4. Audio Playback URLs

**Endpoint:** `GET /coaching/{coaching_id}/audio/{type}`

**Purpose:** Get signed URLs for full audio playback

**Path Parameters:**
- `type`: `original` | `improved`

**Expected Response:**
```json
{
  "coaching_id": "coach_abc123",
  "audio_type": "original",
  "url": "https://s3-presigned-url.../audio.wav",
  "duration_seconds": 18.5,
  "expires_at": "2026-01-16T15:00:00Z"
}
```

**Implementation Notes:**
- Generate presigned S3 URLs with 1-hour expiration
- Support both original and AI-improved full audio
- Include metadata (duration, format)

**Technical Requirements:**
- S3 presigned URL generation
- Store full improved audio file (not just segments)

---

### 5. Practice Session Recording

**Endpoint:** `POST /coaching/{coaching_id}/practice`

**Purpose:** Record user's practice attempt for a specific segment and get comparison feedback

**Request Body:**
```json
{
  "segment_id": 2,
  "practice_audio": "<base64-encoded-audio>"
}
```

**Expected Response:**
```json
{
  "practice_id": "practice_xyz789",
  "segment_id": 2,
  "comparison": {
    "similarity_score": 0.82,
    "pace_match": 0.85,
    "pitch_match": 0.78,
    "energy_match": 0.84
  },
  "feedback": "Good progress! Your pacing is much improved. Try to match the pitch variation more closely in the second half.",
  "needs_more_practice": false
}
```

**Implementation Notes:**
- Accept audio upload for segment practice
- Compare with target improved version
- Analyze similarity metrics (pace, pitch, energy)
- Provide actionable feedback
- Track practice attempts per user/segment

**Technical Requirements:**
- Audio comparison algorithms
- Real-time analysis pipeline
- Practice history storage

---

## Implementation Priority

### High Priority (Core Features)
1. **Interactive Transcript with Segment Audio** - Critical for main user workflow
2. **Waveform Visualization Data** - Enhances user experience significantly
3. **Audio Playback URLs** - Basic functionality for full audio playback

### Medium Priority (Enhanced Features)
4. **Progress Tracker Data** - Motivates users, tracks improvement
5. **Practice Session Recording** - Advanced feature for skill building

---

## Database Schema Changes Required

### New Tables Needed

#### `coaching_sessions` (if not exists)
```sql
CREATE TABLE coaching_sessions (
  coaching_id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  original_audio_url VARCHAR,
  improved_audio_url VARCHAR,
  duration_seconds FLOAT,
  overall_score FLOAT,
  status VARCHAR,
  created_at TIMESTAMP,
  completed_at TIMESTAMP
);
```

#### `transcript_segments`
```sql
CREATE TABLE transcript_segments (
  segment_id SERIAL PRIMARY KEY,
  coaching_id VARCHAR REFERENCES coaching_sessions(coaching_id),
  text TEXT,
  start_time FLOAT,
  end_time FLOAT,
  original_audio_url VARCHAR,
  improved_audio_url VARCHAR,
  issue_type VARCHAR,
  issue_description TEXT,
  severity VARCHAR,
  tip TEXT,
  pace_wpm INT,
  pitch_range_hz FLOAT,
  energy_db FLOAT,
  created_at TIMESTAMP
);
```

#### `practice_sessions`
```sql
CREATE TABLE practice_sessions (
  practice_id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  coaching_id VARCHAR,
  segment_id INT REFERENCES transcript_segments(segment_id),
  audio_url VARCHAR,
  similarity_score FLOAT,
  pace_match FLOAT,
  pitch_match FLOAT,
  energy_match FLOAT,
  feedback TEXT,
  created_at TIMESTAMP
);
```

#### `user_progress`
```sql
CREATE TABLE user_progress (
  user_id VARCHAR,
  date DATE,
  overall_score FLOAT,
  pace_rating VARCHAR,
  pitch_rating VARCHAR,
  energy_rating VARCHAR,
  sessions_count INT,
  PRIMARY KEY (user_id, date)
);
```

---

## Environment Variables Needed

Add to backend `.env`:

```bash
# Text-to-Speech for improved audio generation
ELEVENLABS_API_KEY=your_key_here
# OR
AWS_POLLY_ENABLED=true

# Audio processing settings
SEGMENT_DURATION_SECONDS=7  # Target segment length
MAX_SEGMENT_DURATION=10
MIN_SEGMENT_DURATION=5
```

---

## Frontend Integration Notes

The frontend is currently using **mock data** for:
- Interactive transcript segments (`src/data/mockData.ts` - `mockTranscriptSegments`)
- Progress tracker (`src/data/mockData.ts` - `mockProgressData`)
- Waveform visualization (`src/data/mockData.ts` - `mockWaveformSegments`)

Once the above APIs are implemented, update:
- `src/services/api.ts` - Add new API methods
- `src/types/index.ts` - Add response types if needed
- `src/App.tsx` - Replace mock data with API calls
- Remove mock data imports and display warnings

---

## Testing Checklist

Once implemented, test:
- [ ] Segment audio generation for various speech lengths
- [ ] Audio quality of improved segments
- [ ] S3 signed URL expiration and refresh
- [ ] Progress calculation accuracy
- [ ] Waveform rendering performance
- [ ] Practice session comparison accuracy
- [ ] Database queries performance with multiple users
- [ ] Audio playback cross-browser compatibility

---

## Questions for Backend Team

1. **Audio Segmentation**: Should we use silence detection or fixed boundaries for segments?
2. **TTS Provider**: Preference between ElevenLabs, AWS Polly, or Google Cloud TTS for improved audio?
3. **Storage**: How long should we keep segment audio files? Auto-cleanup policy?
4. **Rate Limiting**: Should we limit practice session submissions per user?
5. **Database**: PostgreSQL schema or prefer JSON storage for flexibility?

---

## Estimated Implementation Time

- Interactive Transcript API: **3-5 days** (complex audio processing)
- Waveform Data API: **1-2 days** (audio analysis)
- Audio Playback URLs: **1 day** (straightforward S3 integration)
- Progress Tracker API: **2-3 days** (database aggregation)
- Practice Session API: **3-4 days** (audio comparison algorithms)

**Total: 10-15 days** for full implementation
