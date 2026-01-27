# S3-First Architecture for Cloud Run Deployment

## Problem

Cloud Run is **stateless and ephemeral**:
- Instances can terminate at any time
- Local files disappear when instance shuts down
- `/tmp` is limited and cleared between deployments
- Cannot rely on local filesystem for persistent storage

## Solution: S3-First Architecture

All persistent files are stored in S3 with a centralized path structure. Local files are **temporary only** during processing.

## S3 Structure

```
s3://speach-analyzer/
  {coaching_id}/                    # e.g., coach_abc123
    input/
      {filename}.wav                # Original audio
    transcript/
      transcript.json               # AWS Transcribe output
    output/
      analysis/
        {stem}_coaching_analysis.json    # Full analysis
      coaching/
        {stem}_coaching_feedback.md      # Claude coaching feedback
        {stem}_prosody_data.txt          # Prosody features
      visualizations/
        {stem}_pitch.svg                 # Pitch chart
        {stem}_intensity.svg             # Intensity chart
        {stem}_pace.svg                  # Pace chart
        # ... other charts
      metrics/
        structured_metrics.json          # Structured metrics
      segments/
        original/
          segment_1.wav                  # Original audio segments
          segment_2.wav
        improved/
          segment_1.wav                  # Improved audio segments
          segment_2.wav
        segments_6.json                  # Cached segments data
      waveform/
        waveform_1000.json               # Cached waveform data
```

## Key Components

### 1. `utils/s3_paths.py` - Centralized Path Management

**Purpose:** Single source of truth for S3 paths

**Usage:**
```python
from utils.s3_paths import get_path_manager, get_s3_key

pm = get_path_manager()

# Get S3 key for analysis file
key = pm.get_analysis_key("coach_123", "audio_stem")
# Returns: "coach_123/output/analysis/audio_stem_coaching_analysis.json"

# Or use convenience function
key = get_s3_key("coach_123", "analysis", stem="audio_stem")
```

**Benefits:**
- No hardcoded paths scattered across codebase
- Easy to change S3 structure in one place
- Type-safe with IDE autocomplete
- Consistent path generation

### 2. `storage_manager.ensure_local_file()` - S3-to-Local Bridge

**Purpose:** Download S3 files to local temp when needed

**Usage:**
```python
# Input can be S3 URL or local path
file_path_or_url = metadata["analysis"]["analysis"]

# Ensure it's local (downloads if S3 URL)
local_path = storage_manager.ensure_local_file(
    file_path_or_url,
    coaching_id="coach_123",
    file_type="analysis"
)

# Now use as normal local file
with open(local_path, 'r') as f:
    data = json.load(f)
```

**How it works:**
1. If input is local path that exists → return as-is
2. If input is S3 URL → download to `/tmp/speak-right/{coaching_id}/{file_type}.ext`
3. Cache downloaded files (don't re-download if already local)

### 3. `storage_manager._find_analysis_files()` - S3-First Discovery

**Purpose:** Find analysis files from S3 (not local filesystem)

**How it works:**
1. **Try S3 first** (Cloud Run compatible):
   - Use `s3_client.head_object()` to check if files exist
   - Generate presigned URLs (valid 24 hours)
   - Return URLs in metadata
2. **Fallback to local** (for development):
   - Use glob to find files in local directories
   - Return local paths

**Result:**
```python
metadata["analysis"] = {
    "analysis": "https://s3.amazonaws.com/presigned-url/analysis.json",
    "coaching_feedback": "https://s3.amazonaws.com/presigned-url/feedback.md",
    "visualizations": "coach_123/output/visualizations/",  # S3 prefix
    "prosody_data": "https://s3.amazonaws.com/presigned-url/prosody.txt"
}
```

## Workflow

### Processing (Upload → Analysis)

```
1. User uploads audio
   ├─ Save to local: /tmp/speak-right/{id}/input/{file}.wav
   └─ Upload to S3: s3://.../{{id}}/input/{file}.wav

2. Process audio (background task)
   ├─ Transcribe (AWS Transcribe uses S3 directly)
   ├─ Analyze locally (vocal analysis, prosody, etc.)
   ├─ Generate coaching (Claude API)
   ├─ Create visualizations
   └─ Upload ALL results to S3
       ├─ analysis/*.json
       ├─ coaching/*.md
       ├─ visualizations/*.svg
       └─ metrics/*.json

3. Update database metadata
   └─ Store directories (for file discovery later)

4. Local /tmp files can be cleaned up
   └─ S3 is source of truth
```

### Retrieval (API Request → Response)

```
1. GET /coaching/{id}/transcript

2. Load metadata from database
   └─ Has: coaching_id, user_id, status, directories

3. Discover files in S3
   ├─ storage_manager._find_analysis_files()
   ├─ Checks S3 for coaching_analysis.json, feedback.md, etc.
   └─ Returns presigned URLs

4. Ensure files are local
   ├─ storage_manager.ensure_local_file()
   ├─ Downloads from S3 if needed
   └─ Returns local temp path

5. Generate segments
   ├─ Read local files (downloaded from S3)
   ├─ Call Claude for intelligent selection
   ├─ Generate improved audio
   └─ Upload segments to S3

6. Return response
   └─ All audio URLs are S3 presigned URLs
```

## Migration Guide

### Before (Local-First)

```python
# ❌ Assumed local files exist
analysis_path = metadata["analysis"]["analysis"]
with open(analysis_path, 'r') as f:
    data = json.load(f)
```

### After (S3-First)

```python
# ✅ Works with S3 URLs and local paths
analysis_path_or_url = metadata.get("analysis", {}).get("analysis")
analysis_path = storage_manager.ensure_local_file(
    analysis_path_or_url, coaching_id, "analysis"
)
with open(analysis_path, 'r') as f:
    data = json.load(f)
```

## Best Practices

### 1. **Always use S3 path utilities**
```python
# ✅ Good
from utils.s3_paths import get_s3_key
key = get_s3_key(coaching_id, "analysis", stem=stem)

# ❌ Bad
key = f"{coaching_id}/output/analysis/{stem}_analysis.json"
```

### 2. **Check S3 first, fallback to local**
```python
# ✅ Good - works in Cloud Run and locally
try:
    s3_client.head_object(Bucket=bucket, Key=key)
    # File exists in S3
except:
    # Try local file
    if os.path.exists(local_path):
        # Use local
```

### 3. **Use ensure_local_file() for reading**
```python
# ✅ Good - handles both S3 and local
local_path = storage_manager.ensure_local_file(path_or_url, id, type)
with open(local_path, 'r') as f:
    data = f.read()

# ❌ Bad - fails if path is S3 URL
with open(path_or_url, 'r') as f:  # Error!
    data = f.read()
```

### 4. **Upload to S3 after processing**
```python
# ✅ Good - persist to S3
with open(local_file, 'rb') as f:
    s3_client.put_object(Bucket=bucket, Key=key, Body=f)

# Local file can now be deleted (or will be cleaned up by Cloud Run)
```

## Environment Variables

```bash
# S3 Configuration
S3_BUCKET=speach-analyzer
AWS_DEFAULT_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Local temp directory (Cloud Run uses /tmp)
STORAGE_DIR=/tmp/speak-right
```

## Testing

### Local Development
- Files stored both locally AND in S3
- Local files checked first for faster development
- S3 still tested for production compatibility

### Cloud Run
- Only S3 files persist
- Local /tmp is ephemeral
- All file access goes through ensure_local_file()

## Future Improvements

1. **Caching:** Cache downloaded S3 files in Redis
2. **CDN:** Use CloudFront for faster file delivery
3. **Lifecycle:** Auto-delete old sessions from S3 after X days
4. **Streaming:** Stream large files instead of downloading fully
5. **Direct S3 reads:** Update services to read from S3 directly (no temp files)

## Summary

**Key Principle:** S3 is the source of truth, local filesystem is temporary.

This architecture ensures SpeakRight works reliably on Cloud Run's stateless infrastructure while maintaining backward compatibility with local development.
