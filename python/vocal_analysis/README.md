# Vocal Analysis for Speech Coaching

AI-powered speech analysis tool that combines AWS Transcribe output with acoustic feature extraction to provide detailed coaching insights.

## 🚀 Quick Start

```bash
# 1. Analyze speech (extract acoustic features + metrics)
python3 vocal_analysis/analyze_speech.py \
  transcript.json \
  audio.wav \
  output/analysis.json

# 2. Generate visualizations (5 graphs)
python3 vocal_analysis/visualize_speech.py \
  output/analysis.json \
  audio.wav \
  output/visualizations/
```

**Example with sample data:**
```bash
# Analyze
python3 vocal_analysis/analyze_speech.py \
  deven_asr_output.json \
  ../output/deven/02-04_04-40.wav \
  output/02-04_04-40_coaching_analysis.json

# Visualize
python3 vocal_analysis/visualize_speech.py \
  output/02-04_04-40_coaching_analysis.json \
  ../output/deven/02-04_04-40.wav \
  output/visualizations/
```

---

## 📋 Overview

This module provides comprehensive speech analysis for coaching purposes by:
- Extracting acoustic features (pitch, intensity, formants, voice quality)
- Calculating speech metrics (rate, filler words, pauses)
- Aligning acoustic features with transcript words
- Generating visual graphs for coaching feedback

Perfect for speech coaches, public speaking trainers, and anyone looking to improve their communication skills.

---

## 🎯 Features

### Speech Metrics
- **Speaking Rate**: Words per minute (WPM)
- **Filler Words**: Detects "uh", "um", "like", "actually", "basically", etc.
- **Pauses**: Identifies long pauses (>0.5s) with timestamps
- **Transcription Confidence**: Average confidence from AWS Transcribe

### Acoustic Features
- **Pitch (F0)**: Mean, std, min, max, range, and time-series contour
- **Intensity**: Loudness variation over time in dB
- **Formants**: F1, F2, F3 values for vowel quality assessment
- **Voice Quality**: Harmonics-to-Noise Ratio (HNR) for clarity
- **Tempo**: Beat-based tempo analysis

### Word-Level Analysis
- Each word aligned with:
  - Timestamp (start/end)
  - Pitch (Hz) at that moment
  - Intensity (dB) at that moment
  - Transcription confidence

### Visualizations
1. **Spectrogram**: Frequency content over time (mel spectrogram)
2. **Pitch Plot**: F0 contour with mean/std bands
3. **Intensity Plot**: Loudness variation with mean/std bands
4. **Combined Plot**: Pitch & intensity on same timeline
5. **Metrics Chart**: Bar charts for key coaching metrics

---

## 📦 Installation

### Dependencies
```bash
pip install praat-parselmouth librosa matplotlib numpy
```

Or if using `uv`:
```bash
uv pip install praat-parselmouth librosa matplotlib numpy
```

### System Requirements
- Python 3.8+
- Audio file formats: WAV, MP3, etc. (librosa supports most formats)
- Transcript format: AWS Transcribe JSON output

---

## 📖 Usage

### 1. Speech Analysis

Extract acoustic features and calculate speech metrics:

```bash
python3 vocal_analysis/analyze_speech.py <transcript.json> <audio.wav> <output.json>
```

**Input:**
- `transcript.json`: AWS Transcribe output with word-level timestamps
- `audio.wav`: Audio file (WAV recommended, but MP3 works too)

**Output:**
- JSON file containing:
  - Full transcript text
  - Speech metrics (rate, fillers, pauses)
  - Acoustic features (pitch, intensity, formants, HNR)
  - Word-level analysis with aligned acoustic features

**Example output structure:**
```json
{
  "metadata": {
    "transcript_file": "deven_asr_output.json",
    "audio_file": "../output/deven/02-04_04-40.wav",
    "job_name": "deven-transcribe"
  },
  "transcript": "Started like 15 years ago...",
  "speech_metrics": {
    "total_words": 523,
    "speaking_rate_wpm": 201.4,
    "filler_word_count": 21,
    "filler_word_ratio": 0.04,
    "pause_count": 3,
    "pauses": [...]
  },
  "acoustic_features": {
    "parselmouth": {
      "pitch_mean_hz": 150.2,
      "pitch_range_hz": 471.0,
      "intensity_mean_db": 68.5,
      ...
    },
    "librosa": {...}
  },
  "word_level_analysis": [
    {
      "word": "Started",
      "start_time": 0.09,
      "end_time": 0.569,
      "pitch_hz": 117.1,
      "intensity_db": 71.6,
      "confidence": 0.988
    },
    ...
  ]
}
```

### 2. Visualization Generation

Generate 5 types of graphs for coaching feedback:

```bash
python3 vocal_analysis/visualize_speech.py <analysis.json> <audio.wav> <output_dir>
```

**Input:**
- `analysis.json`: Output from `analyze_speech.py`
- `audio.wav`: Original audio file
- `output_dir`: Directory to save PNG files

**Output:**
Five high-resolution PNG graphs:
1. `*_spectrogram.png`: Mel spectrogram (frequency heatmap)
2. `*_pitch.png`: Pitch contour with mean/std bands
3. `*_intensity.png`: Intensity contour with mean/std bands
4. `*_combined.png`: Pitch & intensity on shared timeline
5. `*_metrics.png`: Bar charts for speaking rate, fillers, pitch range, pauses

---

## 🔧 Technical Details

### Acoustic Analysis (Parselmouth/Praat)
- **Pitch extraction**: 75-600 Hz range (speech frequency)
- **Intensity**: RMS-based loudness in dB
- **Formants**: Burg algorithm, 5 formants up to 5500 Hz
- **HNR**: Harmonics-to-Noise Ratio for voice quality (0.01s window)

### Librosa Analysis
- **Tempo**: Beat-based tempo detection (BPM)
- **RMS Energy**: Volume variation measurement
- **Zero-Crossing Rate**: Voice quality indicator
- **Spectrogram**: Mel-scale, 128 mel bins, up to 8000 Hz

### Filler Word Detection
Automatically detects common filler words:
- uh, um, ah, er
- like, you know
- actually, basically

### Speaking Rate Guidelines
- **Slow**: < 120 WPM
- **Normal**: 120-160 WPM
- **Fast**: 160-200 WPM
- **Very Fast**: > 200 WPM

### Pitch Variation Assessment
- **Monotone**: < 50 Hz range
- **Varied**: ≥ 50 Hz range (more engaging)

---

## 💡 Use Cases

### 1. Public Speaking Training
- Identify monotone speech patterns
- Detect excessive filler words
- Analyze pacing and pauses
- Track improvement over time

### 2. Presentation Coaching
- Ensure varied pitch for engagement
- Maintain consistent volume
- Reduce nervous fillers
- Optimize speaking rate

### 3. Language Learning
- Practice pronunciation (formants)
- Improve intonation (pitch)
- Develop natural rhythm
- Build confidence (voice quality)

### 4. Podcast Production
- Analyze audio quality (HNR)
- Maintain consistent energy (intensity)
- Remove excessive pauses
- Optimize pacing

---

## 📊 Coaching Insights Examples

The analysis enables insights like:

- *"Your speaking rate is 201 WPM, which is quite fast. Try slowing down to 150-160 WPM for better clarity."*
- *"You used 21 filler words (4% of speech). Aim for <5% by being more deliberate with pauses."*
- *"Your pitch varies by 471 Hz - excellent! This keeps listeners engaged."*
- *"You drop volume at sentence ends (intensity drops 15 dB). Maintain consistent energy."*
- *"Three long pauses detected. Use strategic pauses for emphasis, not uncertainty."*

---

## 🔄 Integration with LLMs

The JSON output is designed to be fed directly to LLMs (GPT-4, Claude, etc.) for personalized coaching:

```python
import json
import openai

# Load analysis
with open('output/analysis.json') as f:
    analysis = json.load(f)

# Generate coaching feedback
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{
        "role": "system",
        "content": "You are a professional speech coach. Analyze the speech data and provide constructive feedback."
    }, {
        "role": "user",
        "content": f"Here is the speech analysis:\n{json.dumps(analysis, indent=2)}\n\nProvide coaching feedback."
    }]
)

print(response.choices[0].message.content)
```

---

## 📝 AWS Transcribe Integration

This module expects AWS Transcribe JSON output format:

### Required Structure
```json
{
  "jobName": "...",
  "results": {
    "transcripts": [{"transcript": "..."}],
    "items": [
      {
        "type": "pronunciation",
        "alternatives": [{"confidence": "0.99", "content": "word"}],
        "start_time": "0.0",
        "end_time": "0.5",
        "speaker_label": "spk_0"
      },
      ...
    ]
  }
}
```

### Getting AWS Transcribe Output
```python
import boto3

transcribe = boto3.client('transcribe')

# Start transcription job
transcribe.start_transcription_job(
    TranscriptionJobName='my-job',
    Media={'MediaFileUri': 's3://bucket/audio.wav'},
    MediaFormat='wav',
    LanguageCode='en-US',
    Settings={'ShowSpeakerLabels': True}
)

# Download results
# (save to file and use with this module)
```

---

## 🐛 Troubleshooting

### "No module named 'parselmouth'"
```bash
pip install praat-parselmouth
```

### "No module named 'librosa'"
```bash
pip install librosa
```

### "AttributeError: 'Intensity' object has no attribute..."
- Ensure you're using the latest parselmouth version
- The code uses Praat's `call()` function for compatibility

### Audio file not loading
- Convert to WAV format: `ffmpeg -i input.mp3 output.wav`
- Ensure sample rate is reasonable (16kHz - 48kHz)

### Visualizations not generating
```bash
pip install matplotlib
```

---

## 🤝 Contributing

This module is part of the Speak Right project. To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests (if available)
5. Submit a pull request

---

## 📄 License

Part of the Speak Right project. See main repository for license details.

---

## 🙏 Acknowledgments

- **Parselmouth**: Python wrapper for Praat (phonetics software)
- **librosa**: Audio analysis library
- **AWS Transcribe**: Speech-to-text with word-level timestamps
- **matplotlib**: Visualization library

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review example output in `output/` directory
3. Open an issue in the main repository

---

**Happy Coaching! 🎤**
