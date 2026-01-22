# SpeakRight Coaching API - Architecture

## System Overview

```
┌─────────────┐
│   Client    │
│  (Web/App)  │
└──────┬──────┘
       │
       │ HTTP/REST
       │
┌──────▼──────────────────────────────────────────────────────┐
│                  FastAPI Server                              │
│                  (api/main.py)                               │
│                                                              │
│  Endpoints:                                                  │
│  • POST /upload-audio        → Upload & start processing    │
│  • GET  /coaching/{id}/status → Check progress              │
│  • GET  /coaching/{id}/metrics → Get speech metrics         │
│  • GET  /coaching/{id}/feedback → Get AI coaching           │
│  • GET  /coaching/{id}/visualizations/{type} → Get charts   │
│  • GET  /coaching/{id}/download → Download all results      │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Background Tasks
       │
┌──────▼──────────────────────────────────────────────────────┐
│         Audio Processor Service                              │
│         (services/audio_processor.py)                        │
│                                                              │
│  Pipeline:                                                   │
│  1. Upload audio to S3                                       │
│  2. Transcribe with AWS Transcribe                           │
│  3. Save transcript JSON                                     │
│  4. Run vocal analysis pipeline                              │
│  5. Upload results to S3                                     │
└──────┬──────────────────────────────────────────────────────┘
       │
       ├──────────────────────┬──────────────────┬─────────────┐
       │                      │                  │             │
┌──────▼────────┐  ┌──────────▼─────────┐  ┌────▼─────┐  ┌───▼────┐
│ AWS Transcribe│  │ Vocal Analysis     │  │   AWS    │  │ Claude │
│               │  │ (vocal_analysis/)  │  │   S3     │  │  API   │
│ • Speaker     │  │                    │  │          │  │        │
│   diarization │  │ • Speech metrics   │  │ • Audio  │  │ • AI   │
│ • Word        │  │ • Acoustic analysis│  │ • Trans  │  │   coach│
│   timestamps  │  │ • Visualizations   │  │ • Results│  │   feed │
│ • Confidence  │  │ • Prosody features │  │          │  │   back │
└───────────────┘  └────────────────────┘  └──────────┘  └────────┘
```

## Directory Structure

```
python/
├── api/                          # FastAPI server
│   ├── __init__.py
│   ├── main.py                   # Main server with endpoints
│   ├── models.py                 # Pydantic request/response models
│   └── storage_manager.py        # File & metadata management
│
├── services/                     # Core services
│   ├── __init__.py
│   └── audio_processor.py        # Unified audio processing service
│
├── vocal_analysis/               # Existing vocal analysis
│   ├── analyze_speech.py         # Speech metrics & acoustic analysis
│   ├── visualize_speech.py       # Generate charts/visualizations
│   ├── generate_ssml.py          # AI coaching feedback
│   ├── compare_speech.py         # Compare original vs improved
│   └── run_full_coaching.py      # Full coaching pipeline
│
├── speach_to_text/               # Existing transcription
│   ├── transcribe.py             # AWS Transcribe integration
│   └── transcribe_binary.py
│
├── transcript_enhancement/       # Existing enhancement
│   └── enhance_transcript.py     # ChatGPT enhancement
│
├── text_to_speach/               # Existing TTS
│   └── text_to_speach.py         # ElevenLabs voice cloning
│
├── conversation_scorer/          # Existing scoring
│   └── conversation_scorer.py    # Conversation quality scoring
│
├── utils/                        # Utilities
│   └── aws_utils.py              # AWS S3 utilities
│
├── api_requirements.txt          # API dependencies
├── API_GUIDE.md                  # Complete API documentation
├── QUICKSTART.md                 # Quick start guide
├── ARCHITECTURE.md               # This file
└── test_api_client.py            # Test client
```

## Data Flow

### 1. Upload & Initial Processing

```
Client → FastAPI
  ↓
Generate coaching_id (e.g., coach_a1b2c3d4)
  ↓
Create directory structure:
  /tmp/speak-right/coach_a1b2c3d4/
    ├── input/
    ├── transcript/
    └── output/
        ├── analysis/
        ├── visualizations/
        └── coaching/
  ↓
Save audio file to input/
  ↓
Create metadata JSON
  ↓
Start background processing
  ↓
Return coaching_id to client (immediate response)
```

### 2. Background Processing Pipeline

```
Background Task
  ↓
[1] Upload audio to S3
  → s3://bucket/coaching_sessions/{id}/input/audio.wav
  ↓
[2] Start AWS Transcribe job
  → Wait for completion (polling)
  → Get transcript JSON with:
      • Word-level timestamps
      • Speaker diarization
      • Confidence scores
  ↓
[3] Save transcript locally & to S3
  → transcript.json
  → s3://bucket/coaching_sessions/{id}/transcript/transcript.json
  ↓
[4] Run vocal analysis pipeline:
    ├─ Analyze speech metrics
    │   • Speaking rate (WPM)
    │   • Filler words
    │   • Pause distribution
    │   • Articulation rate
    │
    ├─ Extract acoustic features
    │   • Pitch (F0) contour
    │   • Intensity/energy
    │   • Formants (F1, F2, F3)
    │   • Harmonics-to-noise ratio
    │   • Spectral features
    │
    ├─ Generate visualizations
    │   • Pitch contour (SVG)
    │   • Intensity plot (SVG)
    │   • Spectrogram (SVG)
    │   • Formant plot (SVG)
    │   • Pause distribution (SVG)
    │
    └─ Generate AI coaching feedback
        • Extract prosody features
        • Format for LLM prompt
        • Call Claude API
        • Generate feedback markdown
  ↓
[5] Upload all results to S3
  → s3://bucket/coaching_sessions/{id}/output/...
  ↓
Update metadata status = "completed"
```

### 3. Client Retrieval

```
Client polls /coaching/{id}/status
  ↓
When status = "completed":
  ↓
Client requests metrics
  ← Parse analysis JSON
  ← Return computed scores
  ↓
Client requests feedback
  ← Read coaching markdown
  ← Parse and return structured feedback
  ↓
Client requests visualizations
  ← Return SVG files
  ↓
Optional: Client downloads all as ZIP
  ← Create ZIP of output directory
  ← Return for download
```

## Storage Strategy

### Local Storage (Temporary)

```
/tmp/speak-right/
├── metadata/                    # Session metadata (JSON)
│   ├── coach_abc123.json
│   └── coach_xyz789.json
│
└── coach_abc123/                # Session files
    ├── input/
    │   └── audio.wav
    ├── transcript/
    │   └── transcript.json
    └── output/
        ├── analysis/
        ├── visualizations/
        └── coaching/
```

**Cleanup Strategy:**
- Keep files during processing
- Delete after successful upload to S3
- Keep metadata for session tracking
- Implement TTL cleanup (e.g., delete after 24 hours)

### Cloud Storage (Permanent)

```
s3://speach-analyzer/
└── coaching_sessions/
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

## Scalability Considerations

### Current Architecture (MVP)

- **Concurrency**: Background tasks in same process
- **Storage**: Local filesystem + S3
- **Processing**: Synchronous pipeline
- **Limits**: ~10 concurrent sessions

### Future Enhancements

1. **Task Queue (Celery + Redis)**
   ```
   Client → API → Redis Queue → Worker Pool → S3
   ```

2. **Database (PostgreSQL)**
   ```
   Replace JSON metadata with proper DB:
   - User accounts
   - Session history
   - Metrics storage
   - Search/filtering
   ```

3. **Caching (Redis)**
   ```
   Cache frequently accessed data:
   - Metrics
   - Feedback
   - Visualizations
   ```

4. **CDN (CloudFront)**
   ```
   Serve static assets (visualizations, audio) via CDN
   ```

5. **Microservices**
   ```
   Split into services:
   - Upload Service
   - Transcription Service
   - Analysis Service
   - Feedback Service
   ```

6. **WebSockets**
   ```
   Real-time progress updates instead of polling
   ```

## Security Considerations

### Current

- CORS enabled (configure for production)
- S3 permissions (IAM roles)
- Temporary file storage
- No authentication (mock only)

### Production Requirements

1. **Authentication & Authorization**
   - JWT tokens
   - User sessions
   - Role-based access

2. **Input Validation**
   - File type validation
   - File size limits
   - Rate limiting

3. **Data Privacy**
   - Encryption at rest (S3)
   - Encryption in transit (HTTPS)
   - GDPR compliance (data deletion)

4. **API Security**
   - Rate limiting
   - Request throttling
   - API key management

## Performance Metrics

### Typical Processing Times

| Step | Duration | Bottleneck |
|------|----------|------------|
| Upload | 1-5s | Network bandwidth |
| Transcription | 30-120s | AWS Transcribe queue |
| Analysis | 10-30s | Audio processing |
| Visualizations | 5-10s | Matplotlib rendering |
| AI Coaching | 20-40s | Claude API latency |
| Upload to S3 | 5-15s | Network bandwidth |
| **Total** | **2-5 min** | AWS Transcribe |

### Optimization Opportunities

1. **Parallel Processing**
   - Run visualization generation in parallel
   - Pre-process audio while transcribing

2. **Caching**
   - Cache AWS Transcribe results
   - Cache analysis for re-runs

3. **Async I/O**
   - Async S3 uploads
   - Async API calls

## Monitoring & Logging

### Recommended Tools

- **Application Monitoring**: Sentry, DataDog
- **API Monitoring**: Postman Monitors, UptimeRobot
- **Log Aggregation**: ELK Stack, CloudWatch
- **Metrics**: Prometheus + Grafana

### Key Metrics to Track

- Request latency (p50, p95, p99)
- Processing duration per stage
- Error rates by endpoint
- AWS Transcribe success/failure rate
- S3 upload/download times
- Claude API latency
- Active sessions count
- Storage usage (local & S3)

## API Versioning Strategy

Current: `/coaching/{id}/...`

Future: `/v1/coaching/{id}/...`

When breaking changes needed: `/v2/coaching/{id}/...`

## Deployment Options

### 1. Local Development
```bash
python -m api.main --reload
```

### 2. Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r api_requirements.txt
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. AWS ECS/Fargate
- Containerized deployment
- Auto-scaling
- Load balancing

### 4. Kubernetes
- Multi-container orchestration
- Service mesh
- Auto-scaling

### 5. Serverless (Future)
- AWS Lambda for processing
- API Gateway for endpoints
- Step Functions for orchestration
