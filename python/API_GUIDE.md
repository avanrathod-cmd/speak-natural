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
Content-Type: multipart/form-data

audio_file: <file>
user_id: optional_user_id
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/upload-audio" \
  -H "accept: application/json" \
  -F "audio_file=@/path/to/audio.wav" \
  -F "user_id=user_123"
```

**Python Example:**
```python
import requests

url = "http://localhost:8000/upload-audio"
files = {"audio_file": open("audio.wav", "rb")}
data = {"user_id": "user_123"}

response = requests.post(url, files=files, data=data)
result = response.json()
coaching_id = result["coaching_id"]
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
```

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

Response:
```json
{
  "coaching_id": "coach_a1b2c3d4e5f6",
  "overall_score": 7.5,
  "pace_wpm": 145.8,
  "pitch_variation": "good",
  "energy_level": "good",
  "pause_distribution": {
    "pause_count": 12,
    "total_pause_duration": 15.5,
    "average_pause": 1.29
  }
}
```

### 6. Get Detailed Coaching Feedback

```bash
GET /coaching/{coaching_id}/feedback
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

### 7. Get Visualizations

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

### 8. Download All Results

```bash
GET /coaching/{coaching_id}/download
```

Downloads a ZIP file containing:
- Original audio
- Transcript JSON
- Analysis JSON
- All visualizations (SVG files)
- Coaching feedback (Markdown)
- Prosody data

### 9. List All Sessions

```bash
GET /sessions?user_id=optional_user_id
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

### 10. Delete Session

```bash
DELETE /coaching/{coaching_id}?keep_s3=true
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
          ├── visualizations/
          │   ├── pitch_contour.svg
          │   ├── intensity_plot.svg
          │   ├── spectrogram.svg
          │   ├── formant_plot.svg
          │   └── pause_distribution.svg
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

# 1. Upload audio
upload_response = requests.post(
    "http://localhost:8000/upload-audio",
    files={"audio_file": open("speech.wav", "rb")}
)
coaching_id = upload_response.json()["coaching_id"]
print(f"Coaching ID: {coaching_id}")

# 2. Poll status until complete
while True:
    status_response = requests.get(
        f"http://localhost:8000/coaching/{coaching_id}/status"
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
    f"http://localhost:8000/coaching/{coaching_id}/metrics"
).json()
print(f"Overall Score: {metrics['overall_score']}/10")
print(f"Speaking Pace: {metrics['pace_wpm']} WPM")

# 4. Get feedback
feedback = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/feedback"
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
        f"http://localhost:8000/coaching/{coaching_id}/visualizations/{viz_type}"
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
