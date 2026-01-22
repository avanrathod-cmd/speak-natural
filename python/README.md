# Speech Analysis & Coaching System

A comprehensive Python-based speech analysis system that provides detailed acoustic analysis, transcription, and visual coaching feedback for improving speaking skills.

## Features

### 1. Speech Analysis (`vocal_analysis/analyze_speech.py`)
- **Acoustic Feature Extraction** using Parselmouth (Praat)
  - Pitch (F0) analysis with contour tracking
  - Intensity (loudness) measurements
  - Voice quality metrics (Harmonics-to-Noise Ratio)
  - Formant analysis
- **Speech Metrics Calculation**
  - Speaking rate (words per minute)
  - Filler word detection and counting
  - Pause analysis
  - Word-level acoustic alignment
- **Librosa Audio Analysis**
  - Tempo detection
  - Energy analysis
  - Voice quality indicators

### 2. Speech Visualization (`vocal_analysis/visualize_speech.py`)
Generates high-quality SVG visualizations:
- **Pitch Contour Plot** with word labels and timing bands
- **Intensity Plot** showing volume variations
- **Mel Spectrogram** for frequency content analysis
- **Combined Analysis** with pitch and intensity overlay
- **Metrics Summary** bar charts

### 3. Speech Comparison (`vocal_analysis/compare_speech.py`) ( NEW
Compare two speeches side-by-side with multiple visualization types:
- **Side-by-Side Pitch Comparison** - Visual comparison with word labels
- **Overlaid Pitch Contours** - Direct overlay for pattern comparison
- **Normalized Pitch Comparison** - Relative pitch changes from mean
- **Metrics Comparison Bars** - Bar charts for all key metrics
- **Detailed Comparison Table** - Comprehensive metrics table with better/worse indicators

## Installation

```bash
# Install dependencies
pip install praat-parselmouth librosa numpy matplotlib

# Or using uv (recommended)
uv pip install praat-parselmouth librosa numpy matplotlib
```

## Usage

### Single Speech Analysis

```bash
# Step 1: Analyze speech (requires AWS Transcribe JSON output)
python vocal_analysis/analyze_speech.py \
  transcript.json \
  audio.wav \
  output_coaching.json

# Step 2: Generate visualizations
python vocal_analysis/visualize_speech.py \
  output_coaching.json \
  audio.wav \
  visualizations_output_dir/
```

**Output Files:**
- `*_spectrogram.svg` - Frequency content over time
- `*_pitch.svg` - Pitch contour with word labels and timing bands
- `*_intensity.svg` - Volume variations over time
- `*_combined.svg` - Pitch and intensity together
- `*_metrics.svg` - Summary bar charts

### Speech Comparison Mode

Compare two speeches to track improvement or analyze differences:

```bash
python vocal_analysis/compare_speech.py \
  coaching_file1.json \
  coaching_file2.json \
  comparison_output_dir/ \
  "Speech 1" \
  "Speech 2"
```

**Output Files:**
- `comparison_pitch_sidebyside.svg` - Side-by-side pitch contours with word labels
- `comparison_pitch_overlaid.svg` - Overlaid pitch patterns for direct comparison
- `comparison_pitch_normalized.svg` - Normalized pitch showing relative patterns
- `comparison_metrics_bars.svg` - Bar chart comparison of all metrics
- `comparison_summary_table.svg` - Detailed table with differences and indicators

**Comparison Features:**
- Visual highlighting of which speech performs better on each metric
- Difference calculations for all metrics
- Color-coded indicators (green = better, orange = worse)
- Normalized pitch comparison removes baseline differences to compare patterns

## Input Format

The system expects AWS Transcribe JSON output with:
- Word-level timestamps
- Confidence scores
- Speaker labels (optional)

Example structure:
```json
{
  "results": {
    "transcripts": [{"transcript": "..."}],
    "items": [
      {
        "type": "pronunciation",
        "start_time": "0.5",
        "end_time": "1.0",
        "alternatives": [{"content": "word", "confidence": "0.99"}]
      }
    ]
  }
}
```

## Output Data

The analysis produces a comprehensive JSON file with:

```json
{
  "metadata": {...},
  "transcript": "full text",
  "speech_metrics": {
    "total_words": 150,
    "speaking_rate_wpm": 145.2,
    "filler_word_count": 5,
    "pause_count": 8,
    ...
  },
  "acoustic_features": {
    "parselmouth": {
      "pitch_mean_hz": 180.5,
      "pitch_range_hz": 120.3,
      "pitch_contour": [...],
      "intensity_contour": [...],
      ...
    }
  },
  "word_level_analysis": [
    {
      "word": "hello",
      "start_time": 0.5,
      "end_time": 0.9,
      "pitch_hz": 185.2,
      "intensity_db": 65.3
    }
  ]
}
```

## Coaching Metrics

The system analyzes and compares:

### Speech Delivery
- **Speaking Rate**: Target ~150 WPM for clear communication
- **Filler Words**: Tracks "um", "uh", "like", etc. (Target <5%)
- **Pauses**: Long pauses >0.5s that may indicate uncertainty

### Voice Quality
- **Pitch Variation**: Good speakers use >50 Hz range for expressiveness
- **Volume Variation**: Dynamic speakers use >10 dB range
- **Voice Quality (HNR)**: Harmonics-to-Noise Ratio >10 dB indicates clear voice

### Acoustic Features
- **Pitch Contour**: F0 tracking showing intonation patterns
- **Intensity**: Loudness measurements showing emphasis
- **Formants**: Vowel quality indicators

## Visualization Features

All visualizations are generated as **SVG** (Scalable Vector Graphics):
-  Infinite zoom without quality loss
-  Smaller file sizes for graphs
-  Editable in vector graphics software
-  Perfect for reports and presentations

### Pitch Plot with Word Labels
- Words displayed at their exact timing
- Green bands show word duration (band spread visualization)
- Smart sampling prevents overcrowding
- Arrows connect labels to pitch points

### Comparison Visualizations
- Side-by-side layouts for easy comparison
- Color-coded graphs (blue vs. purple)
- Normalized views for pattern comparison
- Detailed metrics tables with improvement indicators

## Example Workflow

### Track Speaking Improvement

```bash
# Analyze baseline speech
python vocal_analysis/analyze_speech.py \
  baseline_transcript.json baseline.wav baseline_coaching.json

# Analyze improved speech (after practice)
python vocal_analysis/analyze_speech.py \
  improved_transcript.json improved.wav improved_coaching.json

# Compare the two
python vocal_analysis/compare_speech.py \
  baseline_coaching.json \
  improved_coaching.json \
  comparison/ \
  "Before Practice" \
  "After Practice"
```

## Tips for Best Results

1. **Audio Quality**: Use clear recordings with minimal background noise
2. **Speaking Pace**: Natural speaking pace works best for analysis
3. **Comparison**: Compare similar speech types (e.g., presentations vs presentations)
4. **Metrics Interpretation**:
   - Speaking rate: 130-160 WPM is ideal for most contexts
   - Pitch variation: More variation = more engaging
   - Filler words: Lower is better, but some are natural
   - Pauses: Strategic pauses are good; excessive pauses may indicate issues

## Dependencies

- **praat-parselmouth**: Phonetic analysis (Praat integration)
- **librosa**: Audio processing and feature extraction
- **numpy**: Numerical computations
- **matplotlib**: Visualization generation

## License

[Your License Here]

## Contributing

Contributions welcome! Please feel free to submit pull requests or open issues.
