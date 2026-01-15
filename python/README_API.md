# SpeakRight Coaching API 🎙️

AI-powered speech coaching and analysis service with FastAPI.

## What's New

This API provides a modular, production-ready interface to the SpeakRight speech coaching pipeline:

- ✅ **Unified Audio Processing**: Single service that handles audio → transcript → full analysis
- ✅ **FastAPI Server**: RESTful API with automatic OpenAPI documentation
- ✅ **S3 Integration**: Automatic upload of inputs and outputs to cloud storage
- ✅ **Request ID System**: Unique coaching session IDs with nested folder structure
- ✅ **Background Processing**: Non-blocking audio processing with status polling
- ✅ **Modular Architecture**: Easy to extend with new features

## Quick Start

### 1. Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your AWS and API keys
```

### 2. Run Server

```bash
# Development mode
python -m api.main --reload

# Production mode
python -m api.main --host 0.0.0.0 --port 8000

# Using Docker
docker-compose up
```

### 3. Test API

```bash
# Use test client
python test_api_client.py path/to/audio.wav

# Or use cURL
curl -X POST "http://localhost:8000/upload-audio" \
  -F "audio_file=@audio.wav"
```

## Features

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload-audio` | POST | Upload audio and start coaching |
| `/coaching/{id}/status` | GET | Check processing status |
| `/coaching/{id}/metrics` | GET | Get speech metrics (score, pace, pitch, etc.) |
| `/coaching/{id}/feedback` | GET | Get AI coaching feedback |
| `/coaching/{id}/visualizations/{type}` | GET | Get visualization (pitch, intensity, etc.) |
| `/coaching/{id}/download` | GET | Download all results as ZIP |
| `/sessions` | GET | List all coaching sessions |

### Key Metrics Provided

- **Overall Score** (0-10): Composite speaking quality score
- **Speaking Pace**: Words per minute (WPM)
- **Pitch Variation**: good / moderate / needs improvement
- **Energy Level**: good / moderate / low
- **Pause Distribution**: Count, duration, and patterns
- **Filler Words**: Count and ratio
- **Voice Quality**: Harmonics-to-noise ratio

### Visualizations Generated

1. **Pitch Contour** - Pitch variation over time
2. **Intensity Plot** - Energy/volume over time
3. **Spectrogram** - Frequency spectrum analysis
4. **Formant Plot** - Vowel resonances (F1, F2, F3)
5. **Pause Distribution** - Timing and frequency of pauses

## Architecture

```
Client → FastAPI Server → Audio Processor Service
                ↓
        1. Upload to S3
        2. AWS Transcribe
        3. Vocal Analysis
        4. AI Coaching
        5. Upload Results
                ↓
        Return coaching_id
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

## Directory Structure

```
python/
├── api/                      # FastAPI server
│   ├── main.py              # Endpoints
│   ├── models.py            # Request/response models
│   └── storage_manager.py   # File management
│
├── services/                # Core services
│   └── audio_processor.py   # Unified processing pipeline
│
├── vocal_analysis/          # Analysis modules (existing)
├── speach_to_text/          # Transcription (existing)
├── transcript_enhancement/  # Enhancement (existing)
├── text_to_speach/          # TTS (existing)
├── conversation_scorer/     # Scoring (existing)
│
├── API_GUIDE.md            # Complete API documentation
├── QUICKSTART.md           # Quick start guide
├── ARCHITECTURE.md         # System architecture
├── test_api_client.py      # Test client
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose setup
```

## Usage Examples

### Python Client

```python
import requests
import time

# Upload audio
response = requests.post(
    "http://localhost:8000/upload-audio",
    files={"audio_file": open("speech.wav", "rb")}
)
coaching_id = response.json()["coaching_id"]

# Wait for completion
while True:
    status = requests.get(
        f"http://localhost:8000/coaching/{coaching_id}/status"
    ).json()
    if status["status"] == "completed":
        break
    time.sleep(5)

# Get metrics
metrics = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/metrics"
).json()

print(f"Score: {metrics['overall_score']}/10")
print(f"Pace: {metrics['pace_wpm']} WPM")
print(f"Pitch: {metrics['pitch_variation']}")
```

### JavaScript Client

```javascript
// Upload audio
const formData = new FormData();
formData.append('audio_file', audioFile);

const uploadResponse = await fetch('http://localhost:8000/upload-audio', {
  method: 'POST',
  body: formData
});

const { coaching_id } = await uploadResponse.json();

// Poll status
const checkStatus = async () => {
  const response = await fetch(`http://localhost:8000/coaching/${coaching_id}/status`);
  const { status } = await response.json();
  return status;
};

while (await checkStatus() !== 'completed') {
  await new Promise(resolve => setTimeout(resolve, 5000));
}

// Get results
const metrics = await fetch(`http://localhost:8000/coaching/${coaching_id}/metrics`)
  .then(r => r.json());

console.log(`Score: ${metrics.overall_score}/10`);
```

## Standalone Usage (Without API)

Process audio directly without running the server:

```bash
python -m services.audio_processor audio.wav --request-id my_test
```

Or in Python:

```python
from services.audio_processor import process_audio_simple

results = process_audio_simple(
    audio_file_path="audio.wav",
    request_id="my_test"
)

print(results["coaching_id"])
print(results["analysis"])
```

## Session Folder Structure

Each coaching session creates organized folders:

```
/tmp/speak-right/
└── coach_abc123/
    ├── input/
    │   └── audio.wav
    ├── transcript/
    │   └── transcript.json
    └── output/
        ├── analysis/
        │   └── coaching_analysis.json
        ├── visualizations/
        │   ├── pitch_contour.svg
        │   ├── intensity_plot.svg
        │   ├── spectrogram.svg
        │   ├── formant_plot.svg
        │   └── pause_distribution.svg
        └── coaching/
            ├── coaching_feedback.md
            └── prosody_data.txt
```

## S3 Storage Structure

All files are automatically uploaded to S3:

```
s3://speach-analyzer/
└── coaching_sessions/
    └── coach_abc123/
        ├── input/
        ├── transcript/
        └── output/
```

## API Documentation

Interactive documentation available when server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

Required:
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `ANTHROPIC_API_KEY` - For AI coaching feedback

Optional:
- `AWS_DEFAULT_REGION` (default: ap-south-1)
- `S3_BUCKET` (default: speach-analyzer)
- `STORAGE_DIR` (default: /tmp/speak-right)
- `OPENAI_API_KEY` - For transcript enhancement
- `ELEVENLABS_API_KEY` - For voice cloning

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Future Roadmap

Based on your requirements, planned features include:

### Phase 1 (Current) ✅
- [x] Audio upload endpoint
- [x] Coaching session ID generation
- [x] S3 integration
- [x] Overall metrics
- [x] Basic feedback

### Phase 2 (Next)
- [ ] Record audio endpoint (instead of upload)
- [ ] Atomic segment analysis (5-10 sec segments)
- [ ] Improved audio generation per segment
- [ ] Waveform visualization API
- [ ] Section highlighting (good vs needs improvement)

### Phase 3 (Future)
- [ ] User authentication (JWT)
- [ ] Database integration (PostgreSQL)
- [ ] User history / past recordings
- [ ] Webhook notifications
- [ ] WebSocket for real-time updates
- [ ] Comparison between multiple recordings
- [ ] Progress tracking over time

## Performance

Typical processing time: **2-5 minutes**

Breakdown:
- Upload: 1-5s
- Transcription: 30-120s ⏱️ (main bottleneck)
- Analysis: 10-30s
- Visualizations: 5-10s
- AI Coaching: 20-40s
- Upload to S3: 5-15s

## Troubleshooting

**Server won't start:**
```bash
lsof -i :8000  # Check if port is in use
python -m api.main --port 8080  # Use different port
```

**AWS errors:**
- Verify credentials in `.env`
- Check S3 bucket exists
- Ensure AWS Transcribe available in region

**No AI coaching:**
- Verify `ANTHROPIC_API_KEY` in `.env`
- Use `skip_coaching=True` to test without AI

## Contributing

This is a modular architecture designed for easy extension:

1. **Add new endpoints**: Edit `api/main.py`
2. **Add new metrics**: Edit `vocal_analysis/analyze_speech.py`
3. **Add new visualizations**: Edit `vocal_analysis/visualize_speech.py`
4. **Add new processing steps**: Edit `services/audio_processor.py`

## Documentation

- [QUICKSTART.md](./QUICKSTART.md) - Get started in 5 minutes
- [API_GUIDE.md](./API_GUIDE.md) - Complete API reference
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design details

## License

[Your License Here]

## Support

For issues or questions, please refer to:
- Interactive API docs: http://localhost:8000/docs
- Architecture documentation: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Test examples: `test_api_client.py`
