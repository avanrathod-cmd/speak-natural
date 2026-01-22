# Speech Coaching Pipeline

Complete end-to-end pipeline for speech analysis, visualization, and AI-powered coaching.

## Quick Start

```bash
# Full pipeline with AI coaching
export ANTHROPIC_API_KEY='your-key-here'
python vocal_analysis/run_full_coaching.py transcript.json audio.wav output/

# Without AI coaching (analysis + visualizations only)
python vocal_analysis/run_full_coaching.py transcript.json audio.wav output/ --skip-coaching
```

## Pipeline Overview

The unified script `run_full_coaching.py` chains together three modules:

### 1. **Speech Analysis** (`analyze_speech.py`)
Extracts detailed acoustic features and speech metrics:
- Pitch (F0) analysis with time-series data
- Intensity/volume measurements
- Speaking rate, pauses, filler words
- Voice quality metrics (HNR)
- Word-level prosody alignment

**Output**: `{output_dir}/analysis/coaching_analysis.json`

### 2. **Visualization** (`visualize_speech.py`)
Generates professional charts and graphs:
- Pitch contour with word labels
- Intensity over time
- Mel spectrogram
- Combined pitch + intensity
- Speech metrics summary

**Output**: `{output_dir}/visualizations/*.svg` (5 charts)

### 3. **AI Coaching** (`generate_ssml.py`)
Uses Claude Opus to analyze speech patterns and provide coaching:
- Critique against USA English norms
- Rating on naturalness scale (1-10)
- Improved SSML showing target speech patterns
- Specific word-by-word guidance
- Practice exercises and progress markers

**Output**:
- `{output_dir}/coaching/coaching_feedback.md`
- `{output_dir}/coaching/prosody_data.txt`

## Input Requirements

### 1. Transcript JSON
AWS Transcribe output format with word-level timestamps:
```json
{
  "results": {
    "transcripts": [{"transcript": "..."}],
    "items": [
      {
        "type": "pronunciation",
        "alternatives": [{"content": "word", "confidence": "0.99"}],
        "start_time": "0.5",
        "end_time": "0.8"
      }
    ]
  }
}
```

### 2. Audio File
- Format: WAV (recommended)
- Quality: 16kHz or higher sample rate
- Mono or stereo audio

## Output Structure

```
output/
├── analysis/
│   └── {audio_name}_coaching_analysis.json  # Complete prosody data
├── visualizations/
│   ├── {audio_name}_pitch.svg                # Pitch contour
│   ├── {audio_name}_intensity.svg            # Volume/loudness
│   ├── {audio_name}_combined.svg             # Pitch + intensity
│   ├── {audio_name}_spectrogram.svg          # Frequency analysis
│   └── {audio_name}_metrics.svg              # Summary dashboard
└── coaching/
    ├── {audio_name}_coaching_feedback.md     # AI coaching report
    └── {audio_name}_prosody_data.txt         # Debug: prosody features
```

## Individual Module Usage

You can also run each module separately:

### Analysis Only
```bash
python vocal_analysis/analyze_speech.py transcript.json audio.wav output.json
```

### Visualizations Only
```bash
python vocal_analysis/visualize_speech.py coaching_analysis.json audio.wav output_dir/
```

### AI Coaching Only
```bash
export ANTHROPIC_API_KEY='your-key'
python vocal_analysis/generate_ssml.py coaching_analysis.json --coaching
```

## Use Cases

### 1. Speech Coaching for Non-Native Speakers
- Identify pitch and emphasis patterns that differ from USA English norms
- Get specific guidance on which words need different stress
- Practice with improved SSML as a reference

### 2. Presentation Skills Training
- Analyze speaking rate and pause placement
- Improve monotone delivery with pitch variation feedback
- Track progress over multiple recordings

### 3. Voice Acting / Dubbing
- Visualize pitch contours for emotion matching
- Compare prosody between original and dubbed versions
- Fine-tune emphasis patterns

### 4. Research & Analysis
- Extract quantitative prosody data for linguistics research
- Generate word-level acoustic features
- Export to CSV or visualization tools

## Dependencies

```bash
pip install parselmouth         # Praat phonetic analysis
pip install librosa            # Audio processing
pip install matplotlib         # Visualizations
pip install anthropic          # AI coaching (optional)
pip install numpy
```

## Environment Variables

```bash
# Required for AI coaching (Step 3)
export ANTHROPIC_API_KEY='sk-ant-...'

# Optional: AWS credentials (if using AWS Transcribe)
export AWS_ACCESS_KEY_ID='...'
export AWS_SECRET_ACCESS_KEY='...'
```

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Set the environment variable before running
- Or use `--skip-coaching` flag to skip AI feedback

### "No module named 'parselmouth'"
```bash
pip install praat-parselmouth
```

### "No module named 'librosa'"
```bash
pip install librosa
```

### Audio file format issues
- Convert to WAV: `ffmpeg -i input.mp3 output.wav`
- Ensure 16kHz+ sample rate: `ffmpeg -i input.wav -ar 16000 output_16k.wav`

## Performance Notes

- **Analysis**: ~5-10 seconds for 2-minute audio
- **Visualizations**: ~10-20 seconds (includes spectrogram generation)
- **AI Coaching**: ~30-60 seconds (depends on speech length and API latency)

Total pipeline time: **~1-2 minutes** for a typical 2-minute speech recording.

## Advanced Options

### Custom Coaching Prompts
Edit `generate_ssml.py` → `create_coaching_prompt()` to customize:
- Target language/dialect (default: USA English)
- Coaching style (formal, conversational, technical)
- Focus areas (pitch, rate, emphasis, pauses)

### Batch Processing
Process multiple files:
```bash
for transcript in transcripts/*.json; do
  audio="${transcript%.json}.wav"
  output="output/$(basename ${transcript%.json})"
  python vocal_analysis/run_full_coaching.py "$transcript" "$audio" "$output"
done
```

## Example Output

**Speech Summary:**
```
📊 Speech Summary:
   • Total words: 523
   • Speaking rate: 201.4 WPM
   • Filler words: 21 (4.0%)
   • Long pauses: 3
   • Pitch range: 470.9 Hz
   • Voice quality: 12.3 dB HNR
```

**AI Coaching Excerpt:**
```markdown
# SECTION 1: SPEECH CRITIQUE

Overall Assessment: 6.5/10

The speaker demonstrates fast speech rate (201 WPM vs ideal 160 WPM)
with good pitch variation but inconsistent emphasis patterns...

# SECTION 2: IMPROVED SSML

<prosody rate="85%">
  Started <emphasis level="moderate">15 to 16 years ago</emphasis>,
  <break time="300ms"/>
  so it was in <emphasis>9th standard</emphasis> when I got introduced
  to programming.
</prosody>

# SECTION 3: COACHING GUIDANCE

Priority Issues:
1. Reduce speaking rate by 15-20%
2. Add natural pauses at clause boundaries
3. Stress content words (nouns, verbs) not function words
...
```

## Contributing

To add new features:
1. Individual modules in `vocal_analysis/*.py`
2. Update `run_full_coaching.py` to chain new module
3. Add tests and documentation

## License

Part of the Speak-Right vocal analysis toolkit.
