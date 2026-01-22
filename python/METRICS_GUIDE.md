# Structured Metrics Guide

## Overview

The SpeakRight system now generates **structured, quantifiable metrics** from speech analysis with tight, documented definitions. These metrics provide clear, actionable feedback using both computational analysis and optional AI insights.

## Metrics Generated

### 1. Overall Score (0-10)

**Composite score** calculated from 5 factors:

- **Pace** (2 points): Ideal 140-180 WPM
- **Filler Words** (2 points): <2% is excellent
- **Pitch Variation** (2 points): >100 Hz range is excellent
- **Energy Variation** (2 points): >5 dB standard deviation is good
- **Voice Quality** (2 points): >15 dB HNR (harmonics-to-noise ratio) is excellent

### 2. Pace (Words Per Minute)

**Tight Definitions:**
- **Excellent**: 140-180 WPM
- **Good (slightly slow)**: 120-140 WPM
- **Good (slightly fast)**: 180-200 WPM
- **Too slow**: <120 WPM
- **Too fast**: >200 WPM

**Ideal:** 140-160 WPM for presentations, 160-180 WPM for conversations

### 3. Pitch Variation

Measured by pitch range (Hz) and standard deviation.

**Tight Definitions:**
- **Excellent**: >100 Hz range with >20 Hz std deviation
- **Good**: >75 Hz range with >15 Hz std
- **Moderate**: >50 Hz range
- **Needs Improvement (monotone)**: <50 Hz range

**Why it matters:** Pitch variation creates engagement and emphasizes key points.

### 4. Energy Level

Measured by intensity (volume) variation in decibels.

**Tight Definitions:**
- **Good**: >5 dB standard deviation
- **Moderate**: 3-5 dB standard deviation
- **Low (flat delivery)**: <3 dB standard deviation

**Why it matters:** Energy variation shows enthusiasm and prevents monotone delivery.

### 5. Pause Distribution

Analyzes frequency and duration of pauses.

**Tight Definitions:**
- **Good**: 1-2 second pauses, occurring every 10-15 words (5-15% pause ratio)
- **Moderate**: Either timing or frequency is appropriate
- **Too frequent**: >15% pause ratio
- **Too rare**: <5% pause ratio
- **Needs improvement**: Neither timing nor frequency is appropriate

**Why it matters:** Strategic pauses allow audience processing and create emphasis.

### 6. Filler Words

Counts "um", "uh", "like", "you know", etc.

**Tight Definitions:**
- **Excellent**: <2% of total words
- **Good**: 2-5%
- **Moderate**: 5-8%
- **Needs improvement**: >8%

**Why it matters:** Excessive fillers reduce credibility and distract listeners.

### 7. Voice Quality

Measured by Harmonics-to-Noise Ratio (HNR) in decibels.

**Tight Definitions:**
- **Excellent (clear)**: >15 dB HNR
- **Good**: 12-15 dB HNR
- **Moderate**: 10-12 dB HNR
- **Needs improvement (breathy/hoarse)**: <10 dB HNR

**Why it matters:** Clear voice quality ensures comprehension and professionalism.

## AI-Enhanced Insights

When `ANTHROPIC_API_KEY` is available, Claude analyzes the feedback to provide:

1. **Top 3 Strengths**: Specific, actionable positives (not generic praise)
2. **Top 3 Improvements**: Specific, actionable areas to work on
3. **Overall Impression**: One-sentence summary
4. **Confidence Level**: High/medium/low based on data quality

## Output Format

Metrics are saved to: `output/metrics/structured_metrics.json`

```json
{
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
    "definition": "Good: Natural pauses (1-2s) every 10-15 words; Too frequent: >15%; Too rare: <5%"
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
    "definition": "Good: >15 dB (clear voice); Moderate: 10-15 dB; Poor: <10 dB (breathy/hoarse)"
  },
  "ai_insights": {
    "top_strengths": [
      "Clear articulation with minimal filler words",
      "Good pace variation that maintains engagement",
      "Strategic pauses that emphasize key points"
    ],
    "top_improvements": [
      "Increase pitch variation in the middle section for more emphasis",
      "Add more energy when transitioning between topics",
      "Reduce speaking pace slightly in complex explanations"
    ],
    "overall_impression": "Strong delivery with excellent clarity and pacing, minor improvements in pitch variation would enhance engagement further.",
    "confidence": "high"
  }
}
```

## API Endpoints

### Get Summary Metrics

```bash
GET /coaching/{coaching_id}/metrics
```

Returns simplified metrics response:

```json
{
  "coaching_id": "coach_abc123",
  "overall_score": 7.5,
  "pace_wpm": 156.3,
  "pitch_variation": "excellent",
  "energy_level": "good",
  "pause_distribution": {
    "pause_count": 12,
    "total_pause_duration": 18.5,
    "average_pause": 1.54
  }
}
```

### Get Detailed Metrics

```bash
GET /coaching/{coaching_id}/metrics/detailed
```

Returns full structured metrics JSON with definitions and AI insights.

## Usage

### In Audio Processing Pipeline

Metrics are automatically generated during processing:

```bash
[1/6] Uploading audio to S3...
[2/6] Transcribing audio...
[3/6] Saving transcript...
[4/6] Running vocal analysis and coaching...
[5/6] Generating structured metrics...
  ✓ Structured metrics saved
  Overall Score: 7.5/10
  Pace: excellent
  Pitch Variation: excellent
  Energy Level: good
[6/6] Uploading results to S3...
```

### Standalone Usage

Generate metrics from existing analysis:

```bash
python -m services.metrics_generator coaching_analysis.json [coaching_feedback.md]
```

### Programmatic Usage

```python
from services.metrics_generator import generate_structured_metrics

metrics = generate_structured_metrics(
    coaching_analysis_path="path/to/coaching_analysis.json",
    coaching_feedback_path="path/to/coaching_feedback.md",  # Optional
    api_key="your-anthropic-key"  # Optional, uses env if not provided
)

print(f"Overall Score: {metrics['overall_score']}/10")
print(f"Pace Rating: {metrics['pace']['rating']}")
print(f"Top Strengths: {metrics['ai_insights']['top_strengths']}")
```

## Backward Compatibility

The system is fully backward compatible:

- **New sessions**: Automatically generate structured metrics
- **Old sessions**: Fall back to legacy metric calculation
- **Missing API key**: Skip AI insights, still generate quantitative metrics

## Customizing Definitions

To adjust rating thresholds, edit `services/metrics_generator.py`:

```python
def rate_pace(pace_wpm: float) -> str:
    """Rate speaking pace."""
    if 140 <= pace_wpm <= 180:  # Adjust these thresholds
        return "excellent"
    # ... etc
```

## Future Enhancements

Planned features:

1. **Segment-level metrics**: 5-10 second atomic segment analysis
2. **Comparison metrics**: Compare multiple recordings over time
3. **Custom rubrics**: Define your own rating criteria
4. **Trend analysis**: Track improvement across sessions
5. **Context-aware ratings**: Adjust definitions based on speech context (presentation vs conversation)

## Definitions Philosophy

All ratings follow these principles:

1. **Objective**: Based on measurable acoustic features
2. **Actionable**: Clear targets for improvement
3. **Context-aware**: Definitions note when context matters
4. **Evidence-based**: Thresholds based on speech research
5. **Understandable**: Plain language explanations included
