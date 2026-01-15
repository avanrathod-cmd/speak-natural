# QuickStart Guide - SpeakRight Coaching API

## 1. Install Dependencies

```bash
cd python
pip install -r api_requirements.txt
```

## 2. Configure Environment

Create `.env` file:

```bash
# Required
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
ANTHROPIC_API_KEY=your_anthropic_key

# Optional (defaults shown)
AWS_DEFAULT_REGION=ap-south-1
S3_BUCKET=speach-analyzer
STORAGE_DIR=/tmp/speak-right
```

## 3. Start the Server

```bash
# Start in development mode
python -m api.main --reload

# Server will run on http://localhost:8000
```

## 4. Test the API

In a new terminal:

```bash
# Option A: Use the test client
python test_api_client.py path/to/audio.wav

# Option B: Use cURL
curl -X POST "http://localhost:8000/upload-audio" \
  -F "audio_file=@path/to/audio.wav"
```

## 5. View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Complete Example

```python
import requests
import time

# 1. Upload audio
response = requests.post(
    "http://localhost:8000/upload-audio",
    files={"audio_file": open("audio.wav", "rb")}
)
coaching_id = response.json()["coaching_id"]

# 2. Wait for completion
while True:
    status = requests.get(
        f"http://localhost:8000/coaching/{coaching_id}/status"
    ).json()

    if status["status"] == "completed":
        break
    time.sleep(5)

# 3. Get results
metrics = requests.get(
    f"http://localhost:8000/coaching/{coaching_id}/metrics"
).json()

print(f"Score: {metrics['overall_score']}/10")
print(f"Pace: {metrics['pace_wpm']} WPM")
```

## Using Standalone Service (Without API)

```bash
# Process audio file directly
python -m services.audio_processor audio.wav --request-id my_test
```

## Troubleshooting

**Server won't start:**
```bash
# Check if port 8000 is available
lsof -i :8000

# Use a different port
python -m api.main --port 8080
```

**AWS errors:**
- Verify AWS credentials in `.env`
- Check S3 bucket exists and is accessible
- Ensure AWS Transcribe is available in your region

**No AI coaching feedback:**
- Verify `ANTHROPIC_API_KEY` is set in `.env`
- Check API key is valid
- Use `--skip-coaching` flag if needed

## Next Steps

- Read [API_GUIDE.md](./API_GUIDE.md) for complete documentation
- Explore [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API testing
- Review example workflow in `test_api_client.py`
