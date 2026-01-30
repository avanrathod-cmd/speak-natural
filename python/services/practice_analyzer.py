"""
Practice scoring service for segment-level practice analysis.

Uses deterministic signal processing (Parselmouth) for low-latency scoring.
Compares user recordings against SSML-based targets using relative deviation
from the user's own baseline (not absolute values).

Scoring categories:
- Emphasis (40%): Did emphasized words have higher energy than baseline?
- Pause (30%): Did pauses match expected durations from SSML?
- Pitch (20%): Was there good pitch variation?
- Speed (10%): Did pace match the target rate?
"""

import re
import os
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np


class EmphasisLevel(Enum):
    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class WordTarget:
    """Target specification for a single word from SSML."""
    word: str
    emphasis: EmphasisLevel
    pause_after_ms: int  # 0 if no pause expected
    rate_modifier: float  # 1.0 = baseline, 0.85 = slow, 1.15 = fast


@dataclass
class SSMLTargetMap:
    """Parsed SSML with word-level targets."""
    words: List[WordTarget]
    overall_rate: float  # from outermost prosody tag
    plain_text: str


def parse_ssml_to_targets(ssml: str) -> SSMLTargetMap:
    """
    Parse SSML string to extract word-level targets.

    Handles:
    - <prosody rate="X%">...</prosody> - pace modifier
    - <emphasis level="moderate|strong">...</emphasis> - stressed words
    - <break time="Xms"/> - expected pauses

    Returns:
        SSMLTargetMap with word targets and overall rate
    """
    if not ssml or not ssml.strip():
        return SSMLTargetMap(words=[], overall_rate=1.0, plain_text="")

    # Extract overall rate from prosody tags (use the first one found)
    rate_match = re.search(r"<prosody[^>]*rate=['\"]?(\d+)%['\"]?", ssml)
    overall_rate = float(rate_match.group(1)) / 100.0 if rate_match else 1.0

    # Find all emphasis spans with their content
    # Pattern matches: <emphasis level="moderate|strong">content</emphasis>
    emphasized_words: Dict[str, EmphasisLevel] = {}
    for match in re.finditer(
        r"<emphasis\s+level=['\"]?(moderate|strong)['\"]?>(.*?)</emphasis>",
        ssml,
        re.IGNORECASE | re.DOTALL
    ):
        level = EmphasisLevel.MODERATE if match.group(1).lower() == "moderate" else EmphasisLevel.STRONG
        content = match.group(2)
        # Extract words from the emphasized content
        for word in re.findall(r"\b[\w']+\b", content):
            emphasized_words[word.lower()] = level

    # Find all break tags and their positions in plain text
    # We'll track which word index should have a pause after it
    breaks_after_word: Dict[int, int] = {}  # word_index -> pause_ms

    # Remove all tags to get plain text
    plain_text = re.sub(r"<[^>]+>", " ", ssml)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    # Tokenize words
    words_raw = plain_text.split()

    # Build target list
    targets: List[WordTarget] = []
    for i, word_text in enumerate(words_raw):
        clean_word = re.sub(r"[^\w']", "", word_text).lower()
        if not clean_word:
            continue

        # Determine emphasis level
        emphasis = emphasized_words.get(clean_word, EmphasisLevel.NONE)

        # Check for expected pause after this word (at punctuation)
        pause_after = 0
        if word_text.rstrip().endswith((".", "!", "?")):
            pause_after = 500  # End of sentence pause
        elif word_text.rstrip().endswith((",", ";", ":")):
            pause_after = 300  # Clause pause

        targets.append(WordTarget(
            word=clean_word,
            emphasis=emphasis,
            pause_after_ms=pause_after,
            rate_modifier=overall_rate
        ))

    # Check for explicit break tags and assign to nearest previous word
    # Find breaks in original SSML and map to word indices
    ssml_working = ssml
    word_idx = 0
    for match in re.finditer(r"<break\s+time=['\"]?(\d+)ms['\"]?\s*/>", ssml):
        pause_ms = int(match.group(1))
        # Find which word this break follows by counting words before the match
        text_before = re.sub(r"<[^>]+>", " ", ssml[:match.start()])
        words_before = len(re.findall(r"\b[\w']+\b", text_before))
        if words_before > 0 and words_before - 1 < len(targets):
            # Update the pause for the word before this break
            targets[words_before - 1] = WordTarget(
                word=targets[words_before - 1].word,
                emphasis=targets[words_before - 1].emphasis,
                pause_after_ms=max(targets[words_before - 1].pause_after_ms, pause_ms),
                rate_modifier=targets[words_before - 1].rate_modifier
            )

    return SSMLTargetMap(
        words=targets,
        overall_rate=overall_rate,
        plain_text=plain_text
    )


def convert_webm_to_wav(webm_data: bytes) -> str:
    """
    Convert webm audio to WAV format using ffmpeg.

    Args:
        webm_data: Raw webm audio bytes

    Returns:
        Path to temporary WAV file (caller must clean up)
    """
    # Write webm to temp file
    webm_fd, webm_path = tempfile.mkstemp(suffix=".webm")
    try:
        os.write(webm_fd, webm_data)
    finally:
        os.close(webm_fd)

    wav_path = webm_path.replace(".webm", ".wav")

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", webm_path,
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                wav_path
            ],
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

        return wav_path

    finally:
        # Clean up webm file
        if os.path.exists(webm_path):
            os.remove(webm_path)


def forced_align_with_whisper(
    audio_path: str,
    expected_text: str
) -> List[Dict[str, Any]]:
    """
    Perform forced alignment using Whisper (tiny model for speed).

    Falls back to uniform distribution if whisper-timestamped is unavailable.

    Args:
        audio_path: Path to WAV file
        expected_text: Expected transcription text

    Returns:
        List of word dicts with start_time, end_time, word
    """
    try:
        import whisper_timestamped as whisper

        # Load tiny model for speed (~75MB, runs in <1s for 15s audio)
        model = whisper.load_model("tiny", device="cpu")

        # Transcribe with word timestamps
        result = whisper.transcribe(model, audio_path, language="en")

        # Extract word timings
        words = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                words.append({
                    "word": re.sub(r"[^\w']", "", word_info["text"].strip()).lower(),
                    "start_time": word_info["start"],
                    "end_time": word_info["end"]
                })

        if words:
            return words

    except ImportError:
        print("whisper-timestamped not available, using fallback alignment")
    except Exception as e:
        print(f"Whisper alignment failed: {e}, using fallback")

    # Fallback: uniform distribution based on audio duration
    try:
        import parselmouth
        sound = parselmouth.Sound(audio_path)
        duration = sound.duration
    except Exception:
        duration = 15.0  # Default assumption

    expected_words = re.findall(r"\b[\w']+\b", expected_text.lower())
    if not expected_words:
        return []

    word_duration = duration / len(expected_words)

    words = []
    for i, word in enumerate(expected_words):
        words.append({
            "word": word,
            "start_time": i * word_duration,
            "end_time": (i + 1) * word_duration
        })

    return words


def extract_acoustic_features(
    audio_path: str,
    word_timings: List[Dict]
) -> Tuple[List[Dict], Dict]:
    """
    Extract per-word acoustic features using Parselmouth.

    Reuses analyze_audio_with_parselmouth() for global baseline extraction,
    then adds per-word feature extraction for scoring.

    Args:
        audio_path: Path to WAV file
        word_timings: List of {word, start_time, end_time}

    Returns:
        Tuple of (word_features, baseline_stats)
    """
    import parselmouth
    from parselmouth.praat import call

    # Reuse existing function for global acoustic analysis
    from vocal_analysis.analyze_speech import analyze_audio_with_parselmouth

    global_features = analyze_audio_with_parselmouth(audio_path)

    # Build baseline from global features
    baseline = {
        "pitch_mean_hz": global_features.get("pitch_mean_hz", 150.0) or 150.0,
        "pitch_std_hz": global_features.get("pitch_std_hz", 20.0) or 20.0,
        "energy_mean_db": global_features.get("intensity_mean_db", 60.0) or 60.0,
        "energy_std_db": global_features.get("intensity_std_db", 5.0) or 5.0,
        "duration_seconds": global_features.get("duration_seconds", 15.0) or 15.0
    }

    # Load sound for per-word extraction
    sound = parselmouth.Sound(audio_path)

    # Per-word features
    word_features = []
    for i, timing in enumerate(word_timings):
        start = timing["start_time"]
        end = timing["end_time"]

        # Ensure valid time range
        if end <= start:
            end = start + 0.1
        if start < 0:
            start = 0
        if end > sound.duration:
            end = sound.duration

        try:
            # Extract word segment
            segment = sound.extract_part(from_time=start, to_time=end)

            # Pitch analysis for this word
            pitch = call(segment, "To Pitch", 0.0, 75, 600)
            pitch_vals = pitch.selected_array['frequency']
            pitch_vals = pitch_vals[pitch_vals > 0]

            # Intensity analysis for this word
            intensity = call(segment, "To Intensity", 75, 0.0, True)
            int_vals = intensity.values[0]
            int_vals = int_vals[int_vals > 0]

            pitch_mean = float(np.mean(pitch_vals)) if len(pitch_vals) > 0 else baseline["pitch_mean_hz"]
            pitch_range = float(np.max(pitch_vals) - np.min(pitch_vals)) if len(pitch_vals) > 1 else 0.0
            energy_db = float(np.mean(int_vals)) if len(int_vals) > 0 else baseline["energy_mean_db"]

        except Exception as e:
            # Use baseline values on error
            pitch_mean = baseline["pitch_mean_hz"]
            pitch_range = 0.0
            energy_db = baseline["energy_mean_db"]

        # Calculate pause to next word
        pause_after_ms = 0.0
        if i < len(word_timings) - 1:
            next_start = word_timings[i + 1]["start_time"]
            pause_after_ms = max(0, (next_start - end) * 1000)  # Convert to ms

        # Calculate relative features (compared to user's own baseline)
        energy_relative = energy_db / baseline["energy_mean_db"] if baseline["energy_mean_db"] > 0 else 1.0
        pitch_relative = pitch_mean / baseline["pitch_mean_hz"] if baseline["pitch_mean_hz"] > 0 else 1.0

        word_features.append({
            "word": timing["word"],
            "start_time": start,
            "end_time": end,
            "energy_db": energy_db,
            "pitch_mean_hz": pitch_mean,
            "pitch_range_hz": pitch_range,
            "energy_relative": energy_relative,
            "pitch_relative": pitch_relative,
            "pause_after_ms": pause_after_ms
        })

    return word_features, baseline


def calculate_scores(
    word_features: List[Dict],
    target_map: SSMLTargetMap,
    baseline: Dict
) -> Dict[str, Any]:
    """
    Calculate practice scores by comparing features to SSML targets.

    Uses relative deviation scoring - compares against user's own baseline,
    not absolute values. This handles different microphones and voice types.

    Scoring categories:
    - Emphasis (40%): Did emphasized words have higher relative energy?
    - Pause (30%): Did pauses match expected durations?
    - Pitch (20%): Was there good pitch variation overall?
    - Speed (10%): Did overall pace match target rate?

    Returns:
        Complete scoring results with overall score and breakdown
    """
    target_words = target_map.words
    word_scores = []

    # Track scores for each category
    emphasis_scores = []
    pause_scores = []

    for i, feature in enumerate(word_features):
        # Find matching target (by index, fallback to no requirements)
        target = target_words[i] if i < len(target_words) else WordTarget(
            word=feature["word"],
            emphasis=EmphasisLevel.NONE,
            pause_after_ms=0,
            rate_modifier=1.0
        )

        # === EMPHASIS SCORE ===
        # For emphasized words, relative energy should be > 1.0 (above baseline)
        emphasis_score = 100.0
        if target.emphasis != EmphasisLevel.NONE:
            energy_rel = feature["energy_relative"]

            # Strong emphasis: expect >= 1.15 (15% louder than baseline)
            # Moderate emphasis: expect >= 1.05 (5% louder)
            threshold = 1.15 if target.emphasis == EmphasisLevel.STRONG else 1.05

            if energy_rel >= threshold:
                emphasis_score = 100.0
            elif energy_rel >= 1.0:
                # Partial credit: linear scale from threshold down to baseline
                emphasis_score = 50 + 50 * (energy_rel - 1.0) / (threshold - 1.0)
            else:
                # Below baseline = poor emphasis (but not zero)
                emphasis_score = max(0, 50 * energy_rel)

            emphasis_scores.append(emphasis_score)

        # === PAUSE SCORE ===
        pause_score = 100.0
        expected_pause = target.pause_after_ms
        actual_pause = feature["pause_after_ms"]

        if expected_pause > 0:
            # Tolerance: within 30% is full marks
            diff_ratio = abs(actual_pause - expected_pause) / expected_pause if expected_pause > 0 else 0

            if diff_ratio <= 0.3:
                pause_score = 100.0
            elif diff_ratio <= 0.5:
                # Gradual decrease from 100 to 70
                pause_score = 100.0 - (diff_ratio - 0.3) * 150
            elif diff_ratio <= 1.0:
                # Gradual decrease from 70 to 30
                pause_score = 70.0 - (diff_ratio - 0.5) * 80
            else:
                # Way off - but still give some credit if pause exists
                pause_score = max(0, 30.0 - (diff_ratio - 1.0) * 30)

            pause_scores.append(pause_score)

        word_scores.append({
            "word": feature["word"],
            "expected_emphasis": target.emphasis.value,
            "energy_relative": round(feature["energy_relative"], 2),
            "emphasis_score": round(emphasis_score, 1),
            "expected_pause_ms": expected_pause,
            "actual_pause_ms": round(actual_pause, 0),
            "pause_score": round(pause_score, 1)
        })

    # === CATEGORY SCORES ===

    # Emphasis category: average of all emphasized word scores
    emphasis_category = sum(emphasis_scores) / len(emphasis_scores) if emphasis_scores else 100.0

    # Pause category: average of all pause scores
    pause_category = sum(pause_scores) / len(pause_scores) if pause_scores else 100.0

    # Pitch category: Overall pitch variation (coefficient of variation)
    # Good speakers have varied pitch - CV > 0.15 is good
    pitch_cv = baseline["pitch_std_hz"] / baseline["pitch_mean_hz"] if baseline["pitch_mean_hz"] > 0 else 0
    pitch_category = min(100, pitch_cv * 500)  # 0.2 CV = 100 (good variation)

    # Speed category: Compare actual duration to expected
    word_count = len(word_features)
    target_wpm = 150 * target_map.overall_rate  # Baseline 150 WPM adjusted by SSML rate
    expected_duration = (word_count / target_wpm) * 60 if target_wpm > 0 else baseline["duration_seconds"]
    actual_duration = baseline["duration_seconds"]

    speed_diff_ratio = abs(actual_duration - expected_duration) / expected_duration if expected_duration > 0 else 0
    speed_category = max(0, 100 - speed_diff_ratio * 100)

    # === OVERALL SCORE (Weighted) ===
    overall = (
        emphasis_category * 0.40 +
        pause_category * 0.30 +
        pitch_category * 0.20 +
        speed_category * 0.10
    )

    return {
        "overall_score": int(round(overall)),
        "emphasis_score": int(round(emphasis_category)),
        "pause_score": int(round(pause_category)),
        "pitch_score": int(round(pitch_category)),
        "speed_score": int(round(speed_category)),
        "passed": overall >= 80,
        "word_breakdown": word_scores,
        "baseline": {
            "energy_mean_db": round(baseline["energy_mean_db"], 1),
            "pitch_mean_hz": round(baseline["pitch_mean_hz"], 1),
            "duration_seconds": round(baseline["duration_seconds"], 2)
        }
    }


def analyze_practice_recording(
    audio_data: bytes,
    improved_ssml: str
) -> Dict[str, Any]:
    """
    Main entry point: analyze a practice recording against SSML target.

    This is the function called by the API endpoint. It orchestrates:
    1. Audio format conversion (webm -> wav)
    2. SSML parsing to extract targets
    3. Forced alignment to get word timings
    4. Acoustic feature extraction with Parselmouth
    5. Score calculation

    Args:
        audio_data: Raw audio bytes (webm format from MediaRecorder)
        improved_ssml: Target SSML string (what user should say)

    Returns:
        Complete analysis results with scores and word breakdown
    """
    wav_path = None

    try:
        # 1. Convert webm to wav
        wav_path = convert_webm_to_wav(audio_data)

        # 2. Parse SSML targets
        target_map = parse_ssml_to_targets(improved_ssml)

        if not target_map.words:
            # No words to analyze - return perfect score
            return {
                "overall_score": 100,
                "emphasis_score": 100,
                "pause_score": 100,
                "pitch_score": 100,
                "speed_score": 100,
                "passed": True,
                "word_breakdown": [],
                "baseline": {
                    "energy_mean_db": 0.0,
                    "pitch_mean_hz": 0.0,
                    "duration_seconds": 0.0
                }
            }

        # 3. Forced alignment to get word timings
        word_timings = forced_align_with_whisper(wav_path, target_map.plain_text)

        if not word_timings:
            # Alignment failed - can't score
            raise ValueError("Could not align audio with expected text")

        # 4. Extract acoustic features
        word_features, baseline = extract_acoustic_features(wav_path, word_timings)

        # 5. Calculate scores
        results = calculate_scores(word_features, target_map, baseline)

        return results

    finally:
        # Cleanup temp files
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
