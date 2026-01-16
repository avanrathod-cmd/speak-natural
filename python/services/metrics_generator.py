"""
Metrics generator service.

Generates structured, quantifiable metrics from coaching analysis and feedback.
Uses AI to create consistent ratings based on tight definitions.
"""

import json
import os
from typing import Dict, Optional
from pathlib import Path


def generate_structured_metrics(
    coaching_analysis_path: str,
    coaching_feedback_path: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Generate structured metrics from coaching analysis and feedback.

    Args:
        coaching_analysis_path: Path to coaching_analysis.json
        coaching_feedback_path: Optional path to coaching_feedback.md
        api_key: Optional Anthropic API key (uses env if not provided)

    Returns:
        Dictionary with structured metrics
    """
    # Load coaching analysis
    with open(coaching_analysis_path, 'r') as f:
        analysis = json.load(f)

    speech_metrics = analysis['speech_metrics']
    acoustic_features = analysis['acoustic_features']

    # Extract quantitative metrics
    pace_wpm = speech_metrics['speaking_rate_wpm']
    filler_ratio = speech_metrics['filler_word_ratio']
    pause_count = speech_metrics['pause_count']

    # Handle different pause data formats
    if 'total_pause_duration_seconds' in speech_metrics:
        total_pause_duration = speech_metrics['total_pause_duration_seconds']
        average_pause = speech_metrics['average_pause_seconds']
    else:
        # Calculate from pauses list if available
        pauses = speech_metrics.get('pauses', [])
        if pauses:
            total_pause_duration = sum(p.get('duration', 0) for p in pauses)
            average_pause = total_pause_duration / len(pauses) if pauses else 0
        else:
            # No pause data available
            total_pause_duration = 0
            average_pause = 0

    pitch_range_hz = acoustic_features['parselmouth']['pitch_range_hz']
    pitch_std = acoustic_features['parselmouth']['pitch_std_hz']
    intensity_mean = acoustic_features['parselmouth']['intensity_mean_db']
    intensity_std = acoustic_features['parselmouth']['intensity_std_db']
    hnr_mean = acoustic_features['parselmouth']['harmonics_to_noise_ratio_mean_db']

    # Calculate ratings using tight definitions
    metrics = {
        "overall_score": calculate_overall_score(
            pace_wpm, filler_ratio, pitch_range_hz, intensity_std, hnr_mean
        ),
        "pace": {
            "words_per_minute": round(pace_wpm, 1),
            "rating": rate_pace(pace_wpm),
            "definition": "Ideal pace: 140-160 WPM for presentations, 160-180 for conversations"
        },
        "pitch_variation": {
            "range_hz": round(pitch_range_hz, 1),
            "std_hz": round(pitch_std, 1),
            "rating": rate_pitch_variation(pitch_range_hz, pitch_std),
            "definition": "Good: >100 Hz range with variety; Moderate: 50-100 Hz; Needs improvement: <50 Hz"
        },
        "energy_level": {
            "intensity_mean_db": round(intensity_mean, 1),
            "intensity_std_db": round(intensity_std, 1),
            "rating": rate_energy_level(intensity_std),
            "definition": "Good: >5 dB variation; Moderate: 3-5 dB; Low: <3 dB"
        },
        "pause_distribution": {
            "pause_count": pause_count,
            "total_duration_seconds": round(total_pause_duration, 2),
            "average_duration_seconds": round(average_pause, 2),
            "rating": rate_pause_distribution(pause_count, average_pause, speech_metrics['total_words']),
            "definition": "Good: Natural pauses (1-2s) every 10-15 words; Too frequent: >15%; Too rare: <5%"
        },
        "filler_words": {
            "count": speech_metrics['filler_word_count'],
            "ratio": round(filler_ratio, 3),
            "rating": rate_filler_words(filler_ratio),
            "definition": "Good: <2%; Moderate: 2-5%; Needs improvement: >5%"
        },
        "voice_quality": {
            "harmonics_to_noise_ratio_db": round(hnr_mean, 1),
            "rating": rate_voice_quality(hnr_mean),
            "definition": "Good: >15 dB (clear voice); Moderate: 10-15 dB; Poor: <10 dB (breathy/hoarse)"
        }
    }

    # If AI feedback is available and API key provided, enhance with AI analysis
    if coaching_feedback_path and os.path.exists(coaching_feedback_path):
        api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            try:
                ai_metrics = extract_ai_metrics(
                    coaching_feedback_path,
                    metrics,
                    api_key
                )
                metrics["ai_insights"] = ai_metrics
            except Exception as e:
                print(f"Warning: Could not generate AI insights: {e}")
                metrics["ai_insights"] = None
        else:
            metrics["ai_insights"] = None
    else:
        metrics["ai_insights"] = None

    return metrics


def calculate_overall_score(
    pace_wpm: float,
    filler_ratio: float,
    pitch_range_hz: float,
    intensity_std: float,
    hnr_mean: float
) -> float:
    """
    Calculate overall speaking score (0-10) based on multiple factors.

    Scoring rubric:
    - Pace: 2 points (ideal 140-180 WPM)
    - Filler words: 2 points (<2% is excellent)
    - Pitch variation: 2 points (>100 Hz range)
    - Energy variation: 2 points (>5 dB std)
    - Voice quality: 2 points (>15 dB HNR)
    """
    score = 0.0

    # Pace scoring (0-2 points)
    if 140 <= pace_wpm <= 180:
        score += 2.0
    elif 120 <= pace_wpm < 140 or 180 < pace_wpm <= 200:
        score += 1.5
    elif 100 <= pace_wpm < 120 or 200 < pace_wpm <= 220:
        score += 1.0
    else:
        score += 0.5

    # Filler words scoring (0-2 points)
    if filler_ratio < 0.02:
        score += 2.0
    elif filler_ratio < 0.05:
        score += 1.5
    elif filler_ratio < 0.08:
        score += 1.0
    else:
        score += 0.5

    # Pitch variation scoring (0-2 points)
    if pitch_range_hz > 100:
        score += 2.0
    elif pitch_range_hz > 75:
        score += 1.5
    elif pitch_range_hz > 50:
        score += 1.0
    else:
        score += 0.5

    # Energy variation scoring (0-2 points)
    if intensity_std > 5:
        score += 2.0
    elif intensity_std > 3:
        score += 1.5
    elif intensity_std > 2:
        score += 1.0
    else:
        score += 0.5

    # Voice quality scoring (0-2 points)
    if hnr_mean > 15:
        score += 2.0
    elif hnr_mean > 12:
        score += 1.5
    elif hnr_mean > 10:
        score += 1.0
    else:
        score += 0.5

    return round(score, 1)


def rate_pace(pace_wpm: float) -> str:
    """Rate speaking pace."""
    if 140 <= pace_wpm <= 180:
        return "excellent"
    elif 120 <= pace_wpm < 140:
        return "good (slightly slow)"
    elif 180 < pace_wpm <= 200:
        return "good (slightly fast)"
    elif pace_wpm < 120:
        return "too slow"
    else:
        return "too fast"


def rate_pitch_variation(pitch_range_hz: float, pitch_std: float) -> str:
    """Rate pitch variation."""
    if pitch_range_hz > 100 and pitch_std > 20:
        return "excellent"
    elif pitch_range_hz > 75 and pitch_std > 15:
        return "good"
    elif pitch_range_hz > 50:
        return "moderate"
    else:
        return "needs improvement (monotone)"


def rate_energy_level(intensity_std: float) -> str:
    """Rate energy level variation."""
    if intensity_std > 5:
        return "good"
    elif intensity_std > 3:
        return "moderate"
    else:
        return "low (flat delivery)"


def rate_pause_distribution(pause_count: int, avg_pause: float, total_words: int) -> str:
    """Rate pause distribution."""
    if total_words == 0:
        return "insufficient data"

    pauses_per_word = pause_count / total_words

    # Check if pauses are appropriately timed (1-2 second pauses are ideal)
    ideal_pause = 1.0 <= avg_pause <= 2.0
    appropriate_frequency = 0.05 <= pauses_per_word <= 0.15

    if ideal_pause and appropriate_frequency:
        return "good"
    elif ideal_pause or appropriate_frequency:
        return "moderate"
    elif pauses_per_word > 0.15:
        return "too frequent"
    elif pauses_per_word < 0.05:
        return "too rare"
    else:
        return "needs improvement"


def rate_filler_words(filler_ratio: float) -> str:
    """Rate filler word usage."""
    if filler_ratio < 0.02:
        return "excellent"
    elif filler_ratio < 0.05:
        return "good"
    elif filler_ratio < 0.08:
        return "moderate"
    else:
        return "needs improvement"


def rate_voice_quality(hnr_mean: float) -> str:
    """Rate voice quality based on harmonics-to-noise ratio."""
    if hnr_mean > 15:
        return "excellent (clear)"
    elif hnr_mean > 12:
        return "good"
    elif hnr_mean > 10:
        return "moderate"
    else:
        return "needs improvement (breathy/hoarse)"


def extract_ai_metrics(
    coaching_feedback_path: str,
    computed_metrics: Dict,
    api_key: str
) -> Dict:
    """
    Use Claude to extract additional insights from coaching feedback.

    Args:
        coaching_feedback_path: Path to coaching_feedback.md
        computed_metrics: Already computed metrics for context
        api_key: Anthropic API key

    Returns:
        Dictionary with AI-extracted insights
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    # Read coaching feedback
    with open(coaching_feedback_path, 'r') as f:
        feedback_content = f.read()

    prompt = f"""Analyze this speech coaching feedback and provide additional insights.

Computed Metrics:
- Overall Score: {computed_metrics['overall_score']}/10
- Pace: {computed_metrics['pace']['words_per_minute']} WPM ({computed_metrics['pace']['rating']})
- Pitch Variation: {computed_metrics['pitch_variation']['rating']}
- Energy Level: {computed_metrics['energy_level']['rating']}
- Pause Distribution: {computed_metrics['pause_distribution']['rating']}

Coaching Feedback:
{feedback_content}

Please provide:
1. Top 3 strengths (be specific, not generic)
2. Top 3 areas for improvement (be specific, actionable)
3. One-sentence overall impression
4. Confidence level in ratings (high/medium/low based on data quality)

Format as JSON:
{{
    "top_strengths": ["strength 1", "strength 2", "strength 3"],
    "top_improvements": ["improvement 1", "improvement 2", "improvement 3"],
    "overall_impression": "one sentence summary",
    "confidence": "high/medium/low"
}}"""

    try:
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        ai_response = response.content[0].text

        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {
                "top_strengths": ["Analysis available in feedback"],
                "top_improvements": ["Analysis available in feedback"],
                "overall_impression": "See detailed feedback for complete analysis",
                "confidence": "medium"
            }

    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return {
            "error": str(e),
            "top_strengths": [],
            "top_improvements": [],
            "overall_impression": "",
            "confidence": "low"
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python metrics_generator.py <coaching_analysis.json> [coaching_feedback.md]")
        sys.exit(1)

    analysis_path = sys.argv[1]
    feedback_path = sys.argv[2] if len(sys.argv) > 2 else None

    metrics = generate_structured_metrics(analysis_path, feedback_path)

    print("\n" + "=" * 80)
    print("STRUCTURED METRICS")
    print("=" * 80)
    print(json.dumps(metrics, indent=2))
