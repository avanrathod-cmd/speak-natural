# SpeakRight Coaching API - Usage Guide

## Overview

The SpeakRight Coaching API provides AI-powered speech coaching and analysis. Upload an audio file and receive detailed feedback on your speaking performance.

## Architecture

```
User Request → FastAPI Server → Audio Processor Service
                    ↓
            1. Upload audio to S3
            2. Transcribe with AWS Transcribe
            3. Analyze speech metrics
            4. Generate visualizations
            5. Generate AI coaching feedback
            6. Upload results to S3
                    ↓
            Return coaching_id to user
```

## Authentication

**All API endpoints require authentication** via Supabase JWT tokens.

### Quick Start

Frontend handles authentication with Supabase:

```javascript
// 1. Sign in with Google (frontend)
const { data } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})

// 2. Get token
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// 3. Use token in API requests
fetch('http://localhost:8000/upload-audio', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

See [AUTH_GUIDE.md](./AUTH_GUIDE.md) for complete authentication documentation.

## Setup

### 1. Install Dependencies

```bash
cd python
uv sync
```

### 2. Configure Environment Variables

Create a `.env` file:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-south-1

# S3 Configuration
S3_BUCKET=speach-analyzer

# AI API Keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Storage
STORAGE_DIR=/tmp/speak-right
```

### 3. Start the Server

```bash
# Development mode with auto-reload
python -m api.main --reload

# Production mode
python -m api.main --host 0.0.0.0 --port 8000

# Or using uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication Endpoints

#### Verify Token

```bash
GET /auth/verify
Authorization: Bearer <token>
```

Test if your Supabase JWT token is valid.

Response:
```json
{
  "authenticated": true,
  "user_id": "uuid-from-supabase",
  "email": "user@example.com",
  "role": "authenticated"
}
```

### 1. Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy"
}
```

### 2. Mock Authentication

```bash
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

Response:
```json
{
  "user_id": "user_abc123",
  "email": "user@example.com",
  "token": "token_xyz789",
  "message": "Signup successful (mock)"
}
```

### 3. Upload Audio for Coaching

```bash
POST /upload-audio
Authorization: Bearer <token>
Content-Type: multipart/form-data

audio_file: <file>
```

**Authentication Required**: Include Supabase JWT token

**cURL Example:**
```bash
TOKEN="your-supabase-jwt-token"

curl -X POST "http://localhost:8000/upload-audio" \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio_file=@/path/to/audio.wav"
```

**Python Example:**
```python
import requests

# Token from Supabase frontend
token = "your-supabase-jwt-token"

headers = {
    "Authorization": f"Bearer {token}"
}

files = {"audio_file": open("audio.wav", "rb")}

response = requests.post(
    "http://localhost:8000/upload-audio",
    headers=headers,
    files=files
)

coaching_id = response.json()["coaching_id"]
print(f"Coaching ID: {coaching_id}")
```

Response:
```json
{
  "coaching_id": "coach_a1b2c3d4e5f6",
  "status": "pending",
  "message": "Audio uploaded successfully. Processing started.",
  "created_at": "2024-01-15T10:30:00"
}
```

### 4. Get Coaching Status

```bash
GET /coaching/{coaching_id}/status
Authorization: Bearer <token>
```

**Authentication Required**: Must be the user who created the session

Response:
```json
{
  "coaching_id": "coach_a1b2c3d4e5f6",
  "status": "completed",
  "progress": "Processing complete",
  "created_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00",
  "error": null
}
```

**Status values:**
- `pending`: Audio uploaded, waiting to start
- `processing`: Analysis in progress
- `completed`: Analysis complete
- `failed`: Error occurred

### 5. Get Overall Metrics

```bash
GET /coaching/{coaching_id}/metrics
```

Returns summary metrics with ratings.

Response:
```json
{
  "coaching_id": "coach_a1b2c3d4e5f6",
  "overall_score": 7.5,
  "pace_wpm": 145.8,
  "pitch_variation": "excellent",
  "energy_level": "good",
  "pause_distribution": {
    "pause_count": 12,
    "total_pause_duration": 15.5,
    "average_pause": 1.29
  }
}
```

**Metrics Explained:**
- **overall_score**: Composite score (0-10) from pace, pitch, energy, fillers, voice quality
- **pace_wpm**: Speaking rate (ideal: 140-180 WPM)
- **pitch_variation**: excellent/good/moderate/needs improvement
- **energy_level**: good/moderate/low
- **pause_distribution**: Statistics about pause timing and frequency

See [METRICS_GUIDE.md](./METRICS_GUIDE.md) for detailed definitions.

### 6. Get Detailed Metrics with Definitions

```bash
GET /coaching/{coaching_id}/metrics/detailed
```

Returns full structured metrics JSON with definitions, raw values, and AI insights.

Response:
```json
{
  "coaching_id": "coach_abc123",
  "metrics": {
    "overall_score": 7.5,
    "pace": {
      "words_per_minute": 156.3,
      "rating": "excellent",
      "definition": "Ideal pace: 140-160 WPM for presentations, 160-180 for conversations"
    },
    "pitch_variation": {
      "range_hz": 112.5,
      "std_hz": 23.4,
      "rating": "excellent",
      "definition": "Good: >100 Hz range with variety; Moderate: 50-100 Hz; Needs improvement: <50 Hz"
    },
    "energy_level": {
      "intensity_mean_db": 68.2,
      "intensity_std_db": 6.3,
      "rating": "good",
      "definition": "Good: >5 dB variation; Moderate: 3-5 dB; Low: <3 dB"
    },
    "pause_distribution": {
      "pause_count": 12,
      "total_duration_seconds": 18.5,
      "average_duration_seconds": 1.54,
      "rating": "good",
      "definition": "Good: Natural pauses (1-2s) every 10-15 words..."
    },
    "filler_words": {
      "count": 3,
      "ratio": 0.015,
      "rating": "excellent",
      "definition": "Good: <2%; Moderate: 2-5%; Needs improvement: >5%"
    },
    "voice_quality": {
      "harmonics_to_noise_ratio_db": 16.8,
      "rating": "excellent (clear)",
      "definition": "Good: >15 dB (clear voice); Moderate: 10-15 dB; Poor: <10 dB"
    },
    "ai_insights": {
      "top_strengths": [
        "Clear articulation with minimal filler words",
        "Good pace variation that maintains engagement",
        "Strategic pauses that emphasize key points"
      ],
      "top_improvements": [
        "Increase pitch variation in the middle section",
        "Add more energy when transitioning between topics",
        "Reduce speaking pace slightly in complex explanations"
      ],
      "overall_impression": "Strong delivery with excellent clarity and pacing...",
      "confidence": "high"
    }
  }
}
```

**Use this endpoint when you need:**
- Complete rating definitions and thresholds
- Raw acoustic measurements
- AI-generated insights (when available)
- Detailed explanations for frontend display

### 7. Get Waveform Visualization Data

```bash
GET /coaching/{coaching_id}/waveform?samples=1000
Authorization: Bearer <token>
```

Returns audio waveform data with color-coded quality segments for interactive visualization.

**Query Parameters:**
- `samples`: Number of waveform peaks (100-5000, default: 1000)

**Response:**
```json
{
  "coaching_id": "coach_abc123",
  "duration_seconds": 18.5,
  "sample_rate": 44100,
  "waveform_data": {
    "peaks": [0.2, 0.5, 0.8, 0.6, ...],
    "sample_count": 1000,
    "sample_interval_ms": 18.5
  },
  "quality_segments": [
    {
      "start_time": 0.0,
      "end_time": 3.2,
      "quality": "good",
      "color": "#10b981",
      "reason": "normal"
    },
    {
      "start_time": 3.2,
      "end_time": 9.5,
      "quality": "warning",
      "color": "#f59e0b",
      "reason": "filler_word"
    },
    {
      "start_time": 9.5,
      "end_time": 18.5,
      "quality": "good",
      "color": "#10b981",
      "reason": "normal"
    }
  ]
}
```

**Quality Segment Colors:**
- `#10b981` (Green): Normal speech
- `#f59e0b` (Orange): Filler words or long pauses (>2s)
- `#3b82f6` (Blue): Low confidence words

**Features:**
- Automatically downsamples audio to requested sample count
- Normalized amplitude values (0.0 to 1.0)
- Results cached for faster subsequent requests
- Different sample counts cached separately

**Usage:**
```javascript
// Fetch waveform data
const response = await fetch(
  `http://localhost:8000/coaching/${coaching_id}/waveform?samples=1000`,
  { headers: { 'Authorization': `Bearer ${token}` } }
)
const { waveform_data, quality_segments } = await response.json()

// Render waveform with quality colors
waveform_data.peaks.forEach((peak, i) => {
  const time = (i / waveform_data.sample_count) * duration_seconds
  const segment = quality_segments.find(s =>
    time >= s.start_time && time < s.end_time
  )
  drawBar(i, peak, segment.color)
})
```

### 8. Get Interactive Transcript with Audio Segments

```bash
GET /coaching/{coaching_id}/transcript?max_segments=6
Authorization: Bearer <token>
```

Returns selected interesting segments from the speech with both original and AI-improved audio clips. Great for creating an interactive transcript where users can hear and compare original vs. improved versions.

**Query Parameters:**
- `max_segments`: Maximum number of segments to return (1-10, default: 6)

**Segments are selected based on:**
- Filler words (um, uh, like, etc.)
- Pace issues (too fast: >180 WPM, too slow: <100 WPM)
- Low confidence transcription (<0.7)
- Good examples of clear speech (pace 140-180 WPM, high confidence >0.9)

**Response:**
```json
{
  "coaching_id": "coach_abc123",
  "segments": [
    {
      "segment_id": 1,
      "start_time": 2.5,
      "end_time": 7.8,
      "duration": 5.3,
      "text": "So um I think that we should like consider this option",
      "word_count": 10,
      "severity": "warning",
      "severity_score": 6.0,
      "quality_score": 0,
      "is_exemplary": false,
      "issues": [
        {
          "type": "filler-words",
          "description": "Contains 3 filler word(s)",
          "tip": "Try pausing instead of using filler words"
        }
      ],
      "primary_issue": {
        "type": "filler-words",
        "description": "Contains 3 filler word(s)",
        "tip": "Try pausing instead of using filler words"
      },
      "metrics": {
        "pace_wpm": 113.2,
        "filler_ratio": 0.3,
        "confidence": 0.942
      },
      "original_audio_url": "https://speach-analyzer.s3.amazonaws.com/coach_abc123/segments/original/segment_1.wav",
      "improved_audio_url": "https://speach-analyzer.s3.amazonaws.com/coach_abc123/segments/improved/segment_1.wav"
    },
    {
      "segment_id": 2,
      "start_time": 15.2,
      "end_time": 21.5,
      "duration": 6.3,
      "text": "The key advantage is the flexibility it provides",
      "word_count": 9,
      "severity": "good",
      "severity_score": 0,
      "quality_score": 25.0,
      "is_exemplary": true,
      "issues": [],
      "primary_issue": null,
      "metrics": {
        "pace_wpm": 85.7,
        "filler_ratio": 0.0,
        "confidence": 0.98
      },
      "original_audio_url": "https://speach-analyzer.s3.amazonaws.com/coach_abc123/segments/original/segment_2.wav",
      "improved_audio_url": "https://speach-analyzer.s3.amazonaws.com/coach_abc123/segments/improved/segment_2.wav"
    }
  ],
  "segment_count": 6
}
```

**Segment Severity Levels:**
- `good`: No significant issues (pace 100-180 WPM, confidence >0.7, no filler words)
- `warning`: Minor issues (severity_score 1-5)
- `error`: Major issues (severity_score >5)

**Improved Audio Features:**
- Filler words removed
- Pacing adjustments for too-fast segments (adds natural pauses)
- Generated using ElevenLabs TTS with configurable voice
- Same text content, just better delivery

**Results Caching:**
- Segments cached locally after first generation
- Different `max_segments` values cached separately
- Segment audio files uploaded to S3 once and reused

**Usage:**
```javascript
// Fetch segments
const response = await fetch(
  `http://localhost:8000/coaching/${coaching_id}/transcript?max_segments=6`,
  { headers: { 'Authorization': `Bearer ${token}` } }
)
const { segments } = await response.json()

// Play original vs improved audio
segments.forEach(segment => {
  console.log(`Segment ${segment.segment_id}: ${segment.text}`)
  console.log(`Issues: ${segment.issues.map(i => i.description).join(', ')}`)

  // Create audio players
  const originalAudio = new Audio(segment.original_audio_url)
  const improvedAudio = new Audio(segment.improved_audio_url)

  // Play comparison
  originalAudio.play()
  originalAudio.onended = () => improvedAudio.play()
})
```

**Configuration:**
Set `ELEVENLABS_VOICE_ID` in `.env` to customize the voice used for improved audio:
```bash
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel voice
```

### 9. Get Detailed Coaching Feedback

```bash
GET /coaching/{coaching_id}/feedback
Authorization: Bearer <token>
```

Response:
```json
{
  "coaching_id": "coach_a1b2c3d4e5f6",
  "general_feedback": "Your speech shows good energy and clarity...",
  "strong_points": [
    "Clear articulation",
    "Good pace variation",
    "Confident tone"
  ],
  "improvements": [
    "Reduce filler words",
    "Add more pauses for emphasis",
    "Vary pitch more in key points"
  ],
  "segments": []
}
```

### 10. Get Visualizations

```bash
GET /coaching/{coaching_id}/visualizations/{viz_type}
```

**Available visualization types:**
- `pitch` - Pitch contour over time
- `intensity` - Energy/volume over time
- `spectrogram` - Frequency spectrum
- `formants` - Formant frequencies
- `pauses` - Pause distribution

**Example:**
```bash
curl "http://localhost:8000/coaching/coach_abc123/visualizations/pitch" \
  --output pitch_chart.svg
```

### 11. Download All Results

```bash
GET /coaching/{coaching_id}/download
Authorization: Bearer <token>
```

Downloads a ZIP file containing:
- Original audio
- Transcript JSON
- Analysis JSON
- All visualizations (SVG files)
- Coaching feedback (Markdown)
- Prosody data

**Example:**
```bash
# Download with proper filename
curl "http://localhost:8000/coaching/coach_abc123/download" \
  -o results.zip

# Or let curl use the server's filename
curl -OJ "http://localhost:8000/coaching/coach_abc123/download"

# Extract the zip file
unzip results.zip
```

### 12. List All Sessions

```bash
GET /sessions
Authorization: Bearer <token>
```

Response:
```json
{
  "sessions": [
    {
      "coaching_id": "coach_abc123",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00",
      "completed_at": "2024-01-15T10:35:00"
    }
  ],
  "count": 1
}
```

### 13. Delete Session

```bash
DELETE /coaching/{coaching_id}?keep_s3=true
Authorization: Bearer <token>
```

Response:
```json
{
  "message": "Coaching session coach_abc123 deleted",
  "s3_files_kept": true
}
```

## Folder Structure

Each coaching session creates a nested folder structure:

```
/tmp/speak-right/
  ├── metadata/
  │   └── coach_abc123.json        # Session metadata
  │
  └── coach_abc123/
      ├── input/
      │   └── audio.wav            # Original audio file
      │
      ├── transcript/
      │   └── transcript.json      # AWS Transcribe output
      │
      └── output/
          ├── analysis/
          │   └── coaching_analysis.json
          │
          ├── metrics/
          │   └── structured_metrics.json    # NEW: Structured metrics with ratings
          │
          ├── visualizations/
          │   ├── pitch_contour.svg
          │   ├── intensity_plot.svg
          │   ├── spectrogram.svg
          │   ├── formant_plot.svg
          │   └── pause_distribution.svg
          │
          ├── waveform/                   # NEW: Waveform cache
          │   ├── waveform_1000.json      # Cached at different sample rates
          │   └── waveform_2000.json
          │
          └── coaching/
              ├── coaching_feedback.md
              └── prosody_data.txt
```

## S3 Storage Structure

Files are uploaded to S3 with the following structure:

```
s3://speach-analyzer/
  └── coaching_sessions/
      └── coach_abc123/
          ├── input/
          │   └── audio.wav
          │
          ├── transcript/
          │   └── transcript.json
          │
          └── output/
              ├── analysis/
              ├── visualizations/
              └── coaching/
```

## Using the Standalone Service

You can also use the audio processor service directly without the API:

```python
from services.audio_processor import process_audio_simple

# Process an audio file
results = process_audio_simple(
    audio_file_path="path/to/audio.wav",
    request_id="my_custom_id",  # Optional
    bucket_name="speach-analyzer",
    skip_coaching=False
)

print(results["coaching_id"])
print(results["status"])
print(results["analysis"])
```

Or from command line:

```bash
python -m services.audio_processor path/to/audio.wav \
  --request-id my_custom_id \
  --bucket speach-analyzer
```

## Complete Example Workflow

```python
import requests
import time

# Get token from Supabase session (frontend)
token = "your-supabase-jwt-token"

headers = {
    "Authorization": f"Bearer {token}"
}

# 1. Upload audio
upload_response = requests.post(
    "http://localhost:8000/upload-audio",
    headers=headers,
    files={"audio_file": open("speech.wav", "rb")}
)
coaching_id = upload_response.json()["coaching_id"]
print(f"Coaching ID: {coaching_id}")

# 2. Poll status until complete
while True:
    status_response = requests.get(
        f"http://localhost:8000/coaching/{coaching_id}/status",
        headers=headers
    )
    status = status_response.json()["status"]
    print(f"Status: {status}")

    if status == "completed":
        break
    elif status == "failed":
        print("Processing failed!")
        exit(1)

    time.sleep(5)

# 3. Get metrics
metrics = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/metrics",
    headers=headers
).json()
print(f"Overall Score: {metrics['overall_score']}/10")
print(f"Speaking Pace: {metrics['pace_wpm']} WPM")

# 4. Get feedback
feedback = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/feedback",
    headers=headers
).json()
print("\nStrong Points:")
for point in feedback["strong_points"]:
    print(f"  - {point}")

print("\nImprovements:")
for improvement in feedback["improvements"]:
    print(f"  - {improvement}")

# 5. Download visualizations
for viz_type in ["pitch", "intensity", "spectrogram"]:
    viz_data = requests.get(
        f"http://localhost:8000/coaching/{coaching_id}/visualizations/{viz_type}",
        headers=headers
    )
    with open(f"{viz_type}.svg", "wb") as f:
        f.write(viz_data.content)
    print(f"Downloaded {viz_type}.svg")
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Error Handling

All endpoints return standard HTTP status codes:
- `200`: Success
- `400`: Bad request (e.g., analysis not yet complete)
- `404`: Resource not found (e.g., invalid coaching_id)
- `500`: Server error

Error response format:
```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "coaching_id": "coach_abc123"
}
```

## Performance Considerations

- Audio processing typically takes 2-5 minutes depending on:
  - Audio length
  - AWS Transcribe job queue
  - AI coaching generation time

- Use background tasks to avoid blocking API responses
- Consider implementing webhooks for completion notifications
- Cache results in Redis for faster retrieval (future enhancement)

## Future Enhancements

Based on your requirements, planned features include:

1. **Audio Recording** (not just upload)
2. **Atomic Segment Analysis** (5-10 second segments with improved versions)
3. **Waveform API** (audio waveform visualization)
4. **Section Highlighting** (good delivery vs needs improvement)
5. **User Authentication** (JWT-based auth)
6. **Database Integration** (PostgreSQL for metadata)
7. **Webhook Notifications** (on completion)
8. **Rate Limiting** (prevent abuse)
9. **Caching** (Redis for metrics/feedback)

## Troubleshooting

**Audio upload fails:**
- Check file format (WAV, MP3, MP4 supported)
- Verify file size (AWS Transcribe limits apply)
- Check AWS credentials

**Transcription fails:**
- Verify S3 permissions
- Check AWS Transcribe quotas
- Ensure audio quality is sufficient

**Coaching generation fails:**
- Verify ANTHROPIC_API_KEY is set
- Check API rate limits
- Ensure analysis completed successfully

## Support

For issues or questions:
1. Check the logs: `tail -f /tmp/speak-right.log`
2. Review S3 bucket contents
3. Test with sample audio files
