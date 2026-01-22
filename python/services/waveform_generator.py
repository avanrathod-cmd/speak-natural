"""
Waveform data generator for audio visualization.

Extracts waveform peaks and maps quality segments based on speech analysis.
"""

import json
import librosa
import numpy as np
from typing import Dict, List, Tuple


def generate_waveform_data(
    audio_path: str,
    coaching_analysis_path: str,
    target_samples: int = 1000
) -> Dict:
    """
    Generate waveform visualization data with quality-coded segments.

    Args:
        audio_path: Path to audio file (WAV)
        coaching_analysis_path: Path to coaching analysis JSON
        target_samples: Number of waveform peaks to return (default: 1000)

    Returns:
        Dictionary with waveform peaks and quality segments
    """
    # Load audio
    audio, sample_rate = librosa.load(audio_path, sr=None, mono=True)
    duration = len(audio) / sample_rate

    # Generate waveform peaks by downsampling
    peaks = generate_peaks(audio, target_samples)

    # Calculate sample interval
    sample_interval_ms = (duration / target_samples) * 1000

    # Load coaching analysis
    with open(coaching_analysis_path, 'r') as f:
        analysis = json.load(f)

    # Generate quality segments from analysis
    quality_segments = generate_quality_segments(analysis)

    return {
        "duration_seconds": round(duration, 2),
        "sample_rate": sample_rate,
        "waveform_data": {
            "peaks": peaks,
            "sample_count": len(peaks),
            "sample_interval_ms": round(sample_interval_ms, 2)
        },
        "quality_segments": quality_segments
    }


def generate_peaks(audio: np.ndarray, target_samples: int) -> List[float]:
    """
    Generate waveform peaks by downsampling audio.

    Takes maximum absolute amplitude in each chunk.

    Args:
        audio: Audio samples array
        target_samples: Target number of peaks

    Returns:
        List of normalized peak amplitudes (0.0 to 1.0)
    """
    # Calculate chunk size
    chunk_size = len(audio) // target_samples

    if chunk_size == 0:
        chunk_size = 1

    peaks = []

    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i + chunk_size]
        if len(chunk) > 0:
            # Take max absolute amplitude in chunk
            peak = np.max(np.abs(chunk))
            peaks.append(float(peak))

    # Normalize peaks to 0.0-1.0 range
    if peaks:
        max_peak = max(peaks)
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]

    # Ensure we have exactly target_samples
    while len(peaks) < target_samples:
        peaks.append(0.0)

    return peaks[:target_samples]


def generate_quality_segments(analysis: Dict) -> List[Dict]:
    """
    Generate quality-coded segments from speech analysis.

    Uses word-level metrics to determine segment quality.

    Args:
        analysis: Coaching analysis dictionary

    Returns:
        List of quality segments with time ranges and colors
    """
    # Get word-level data (handle both formats)
    words = analysis.get('words', [])
    if not words:
        words = analysis.get('word_level_analysis', [])
    speech_metrics = analysis.get('speech_metrics', {})

    if not words:
        # No word data, return single neutral segment
        return [{
            "start_time": 0.0,
            "end_time": analysis.get('total_duration_seconds', 0),
            "quality": "neutral",
            "color": "#6b7280",
            "reason": "No word-level data available"
        }]

    segments = []
    current_segment = None

    # Define quality thresholds
    filler_threshold = 0.05  # 5% filler words is warning
    pause_long_threshold = 2.0  # Pauses > 2s are warnings

    for i, word in enumerate(words):
        start_time = word.get('start_time', 0)
        end_time = word.get('end_time', 0)

        # Determine quality for this word
        quality = determine_word_quality(
            word,
            words,
            i,
            filler_threshold,
            pause_long_threshold
        )

        # Start new segment or extend current
        if current_segment is None:
            current_segment = {
                "start_time": start_time,
                "end_time": end_time,
                "quality": quality["level"],
                "color": quality["color"],
                "reason": quality["reason"]
            }
        elif current_segment["quality"] == quality["level"]:
            # Extend current segment
            current_segment["end_time"] = end_time
        else:
            # Save current and start new
            segments.append(current_segment)
            current_segment = {
                "start_time": start_time,
                "end_time": end_time,
                "quality": quality["level"],
                "color": quality["color"],
                "reason": quality["reason"]
            }

    # Add final segment
    if current_segment:
        segments.append(current_segment)

    # Merge very short segments (< 0.5s)
    segments = merge_short_segments(segments, min_duration=0.5)

    return segments


def determine_word_quality(
    word: Dict,
    all_words: List[Dict],
    index: int,
    filler_threshold: float,
    pause_threshold: float
) -> Dict:
    """
    Determine quality level for a word based on various factors.

    Args:
        word: Current word data
        all_words: All words in transcript
        index: Current word index
        filler_threshold: Threshold for filler word detection
        pause_threshold: Threshold for long pauses

    Returns:
        Dictionary with quality level, color, and reason
    """
    word_text = word.get('word', '').lower()
    confidence = word.get('confidence', 1.0)

    # Check for filler words
    filler_words = {'um', 'uh', 'like', 'you know', 'so', 'actually', 'basically'}
    is_filler = word_text in filler_words

    # Check for long pause before this word
    long_pause_before = False
    if index > 0:
        prev_word = all_words[index - 1]
        gap = word.get('start_time', 0) - prev_word.get('end_time', 0)
        if gap > pause_threshold:
            long_pause_before = True

    # Check for low confidence
    low_confidence = confidence < 0.7

    # Determine quality
    if is_filler:
        return {
            "level": "warning",
            "color": "#f59e0b",  # Orange
            "reason": "filler_word"
        }
    elif long_pause_before:
        return {
            "level": "warning",
            "color": "#f59e0b",  # Orange
            "reason": "long_pause"
        }
    elif low_confidence:
        return {
            "level": "info",
            "color": "#3b82f6",  # Blue
            "reason": "low_confidence"
        }
    else:
        return {
            "level": "good",
            "color": "#10b981",  # Green
            "reason": "normal"
        }


def merge_short_segments(
    segments: List[Dict],
    min_duration: float = 0.5
) -> List[Dict]:
    """
    Merge segments that are too short with adjacent segments.

    Args:
        segments: List of quality segments
        min_duration: Minimum segment duration in seconds

    Returns:
        List of merged segments
    """
    if not segments:
        return []

    merged = []
    current = segments[0].copy()

    for i in range(1, len(segments)):
        segment = segments[i]
        current_duration = current["end_time"] - current["start_time"]

        if current_duration < min_duration:
            # Merge with next segment
            current["end_time"] = segment["end_time"]
            # Keep more severe quality level
            if segment["quality"] == "warning" or current["quality"] != "warning":
                current["quality"] = segment["quality"]
                current["color"] = segment["color"]
                current["reason"] = segment["reason"]
        else:
            # Save current and move to next
            merged.append(current)
            current = segment.copy()

    # Add final segment
    merged.append(current)

    return merged


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python waveform_generator.py <audio.wav> <coaching_analysis.json>")
        sys.exit(1)

    audio_path = sys.argv[1]
    analysis_path = sys.argv[2]

    waveform_data = generate_waveform_data(audio_path, analysis_path)

    print("\n" + "=" * 80)
    print("WAVEFORM DATA")
    print("=" * 80)
    print(json.dumps(waveform_data, indent=2))
