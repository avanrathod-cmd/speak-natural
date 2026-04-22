# Deepgram Migration Plan
## Replace AWS Transcribe with Deepgram Nova-2

### Motivation
AWS Transcribe is expensive and `en-US` handles Indian accents and Hinglish
poorly. Deepgram Nova-2 is cheaper, more accurate on Indian English, and
supports code-switching for Hindi-English (Hinglish) speech.

---

### Deepgram Configuration
- **Model:** `nova-2`
- **Language:** `hi` (Hindi primary)
- **Code switching:** `True` — handles mid-sentence language switches (Hinglish)
- **Diarize:** `True` — speaker separation, replaces AWS `ShowSpeakerLabels`
- **Utterances:** `True` — speaker segments, used to build `speaker_labels`
- **Punctuate:** `True`

---

### Internal Transcript Format (unchanged)

`sales_call_analyzer.py` consumes this shape — we normalize Deepgram output
into it so the analyzer needs zero changes:

```json
{
  "results": {
    "items": [
      {
        "type": "pronunciation",
        "speaker_label": "spk_0",
        "start_time": "0.500",
        "end_time": "0.800",
        "alternatives": [{ "content": "hello", "confidence": "0.99" }]
      }
    ],
    "speaker_labels": {
      "segments": [
        {
          "speaker_label": "spk_0",
          "start_time": "0.500",
          "end_time": "2.000",
          "items": [{ "start_time": "0.500" }, { "start_time": "0.800" }]
        }
      ]
    }
  }
}
```

Deepgram → internal mapping:
| Deepgram field | Internal field |
|---|---|
| `word.word` | `alternatives[0].content` |
| `word.confidence` | `alternatives[0].confidence` (str) |
| `word.start` | `start_time` (str) |
| `word.end` | `end_time` (str) |
| `word.speaker` (int) | `speaker_label` = `"spk_{n}"` |
| `utterance.speaker` (int) | `segments[].speaker_label` |
| `utterance.start/end` | `segments[].start_time/end_time` |
| `utterance.words[].start` | `segments[].items[].start_time` |

---

### Audio Delivery to Deepgram

The existing pipeline uploads audio to S3, then transcribes. Rather than
downloading the file again, we generate a **pre-signed S3 URL** (10-min expiry)
and pass it directly to Deepgram's `transcribe_url()` — no extra download.

---

### Files Changed

#### New: `python/utils/deepgram_client.py`
Single public function `transcribe_from_s3(s3_uri: str) -> dict`:
1. Parse `s3://bucket/key` from the URI
2. Generate a pre-signed URL via `s3_client.generate_presigned_url()`
3. Call Deepgram `transcribe_url()` with Nova-2 + code-switching options
4. Normalize response into the internal format above
5. Return the normalized dict

#### Modified: `python/services/audio_processor.py`
- Remove `from speach_to_text.transcribe import read_transcription`
- Add `from utils.deepgram_client import transcribe_from_s3`
- `transcribe_audio()` calls `transcribe_from_s3(s3_uri)` directly
  (no job name needed — Deepgram is synchronous, no polling)

#### Modified: `python/pyproject.toml`
- Add `deepgram-sdk>=3.0.0`
- Keep `boto3` (still needed for S3); update comment to remove Transcribe mention

#### Modified: `python/.env.example`
- Add `DEEPGRAM_API_KEY=your_deepgram_api_key_here`
- Remove `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` comments about
  Transcribe — keep the vars since they're still needed for S3

#### Deleted: `python/speach_to_text/transcribe.py`
Dead code after migration. The only active caller is `audio_processor.py`.
`convert_transcription_to_ssml` is only used in the legacy binary script.

#### Deleted: `python/speach_to_text/transcribe_binary.py`
Legacy standalone script, not part of the live pipeline. Uses
`convert_transcription_to_ssml` which is AWS-specific and not worth porting.

---

### What Does NOT Change
- S3 audio storage — audio still uploaded to S3 before transcription
- `sales_call_analyzer.py` — no changes, consumes same internal format
- `sales_call_processor.py` — no changes
- `sales_service.py` — no changes
- All other services

---

### New Env Var (Railway)
```
DEEPGRAM_API_KEY=<key from console.deepgram.com>
```

AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) remain in
Railway since they're still used by S3.

---

### Tasks

1. Add `deepgram-sdk` via `uv add deepgram-sdk`
2. Create `python/utils/deepgram_client.py`
3. Update `python/services/audio_processor.py`
4. Update `python/pyproject.toml` comments + `.env.example`
5. Delete `python/speach_to_text/transcribe.py` and `transcribe_binary.py`
6. Set `DEEPGRAM_API_KEY` in Railway
7. Test: upload a call recording and verify the transcript + speaker turns
   look correct in the UI