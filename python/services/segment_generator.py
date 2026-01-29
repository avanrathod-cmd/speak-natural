"""
Segment generator for interactive transcript with audio.

Selects interesting segments from coaching analysis and generates
original + improved audio clips.
"""

import os
import json
import librosa
import soundfile as sf
from typing import Dict, List, Optional
from pathlib import Path
import tempfile
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from services.intelligent_segment_selector import select_segments_with_claude, enrich_segments_with_metadata


def select_interesting_segments(
    analysis: Dict,
    max_segments: int = 6
) -> List[Dict]:
    """
    Select most interesting segments from analysis.

    Selects a mix of:
    - Segments with issues (filler words, pace problems, low confidence)
    - Good examples (well-delivered segments)

    Args:
        analysis: Coaching analysis dictionary
        max_segments: Maximum number of segments to return

    Returns:
        List of selected segments with metadata
    """
    # Try both 'words' and 'word_level_analysis' keys
    words = analysis.get('words', [])
    if not words:
        words = analysis.get('word_level_analysis', [])

    if not words:
        return []

    # Group words into segments (by sentences or pauses)
    raw_segments = group_words_into_segments(words)

    # Score and classify each segment
    scored_segments = []
    for segment in raw_segments:
        score = score_segment(segment, analysis)
        scored_segments.append({
            **segment,
            **score
        })

    # Select diverse set: issues + good examples
    issue_segments = [s for s in scored_segments if s['severity'] in ['warning', 'error']]
    good_segments = [s for s in scored_segments if s['severity'] == 'good' and s['is_exemplary']]

    # Sort by severity/quality
    issue_segments.sort(key=lambda x: x['severity_score'], reverse=True)
    good_segments.sort(key=lambda x: x['quality_score'], reverse=True)

    # Take up to 3 issues and 3 good examples
    num_issues = min(3, len(issue_segments))
    num_good = min(max_segments - num_issues, len(good_segments))

    selected = issue_segments[:num_issues] + good_segments[:num_good]

    # Sort by time
    selected.sort(key=lambda x: x['start_time'])

    # Assign IDs
    for i, segment in enumerate(selected, 1):
        segment['segment_id'] = i

    return selected


def group_words_into_segments(words: List[Dict]) -> List[Dict]:
    """
    Group words into segments based on pauses and sentence boundaries.

    Target: 5-10 second segments

    Args:
        words: List of word dictionaries with timestamps

    Returns:
        List of segment dictionaries
    """
    segments = []
    current_segment = []
    current_start = None

    for i, word in enumerate(words):
        word_text = word.get('word', '')
        start_time = word.get('start_time', 0)
        end_time = word.get('end_time', 0)

        if current_start is None:
            current_start = start_time

        current_segment.append(word)

        # Check for segment boundary
        should_break = False

        # Check duration (5-10 seconds)
        segment_duration = end_time - current_start
        if segment_duration >= 10:
            should_break = True

        # Check for sentence end
        if word_text.endswith(('.', '!', '?')):
            if segment_duration >= 3:  # Minimum 3 seconds
                should_break = True

        # Check for long pause after this word
        if i < len(words) - 1:
            next_word = words[i + 1]
            pause = next_word.get('start_time', 0) - end_time
            if pause > 1.0 and segment_duration >= 3:
                should_break = True

        # Last word
        if i == len(words) - 1:
            should_break = True

        if should_break and current_segment:
            # Create segment
            segment_text = ' '.join([w.get('word', '') for w in current_segment])
            segments.append({
                'text': segment_text,
                'start_time': current_start,
                'end_time': end_time,
                'words': current_segment,
                'word_count': len(current_segment)
            })
            current_segment = []
            current_start = None

    return segments


def score_segment(segment: Dict, analysis: Dict) -> Dict:
    """
    Score a segment to determine if it's interesting (issue or exemplary).

    Args:
        segment: Segment dictionary
        analysis: Full coaching analysis

    Returns:
        Dictionary with severity, scores, and issue information
    """
    words = segment['words']
    duration = segment['end_time'] - segment['start_time']
    word_count = segment['word_count']

    # Calculate pace
    pace_wpm = (word_count / duration) * 60 if duration > 0 else 0

    # Check for filler words
    filler_words = {'um', 'uh', 'like', 'you know', 'so', 'actually', 'basically', 'literally'}
    filler_count = sum(1 for w in words if w.get('word', '').lower() in filler_words)
    filler_ratio = filler_count / word_count if word_count > 0 else 0

    # Check average confidence
    avg_confidence = sum(w.get('confidence', 1.0) for w in words) / len(words) if words else 1.0

    # Determine issues
    issues = []
    severity_score = 0

    if filler_count > 0:
        issues.append({
            'type': 'filler-words',
            'description': f"Contains {filler_count} filler word(s)",
            'tip': "Try pausing instead of using filler words"
        })
        severity_score += filler_count * 2

    if pace_wpm > 180:
        issues.append({
            'type': 'too-fast',
            'description': f"Too fast ({int(pace_wpm)} WPM)",
            'tip': "Slow down and add pauses for clarity"
        })
        severity_score += (pace_wpm - 180) / 10

    elif pace_wpm < 100 and pace_wpm > 0:
        issues.append({
            'type': 'too-slow',
            'description': f"Too slow ({int(pace_wpm)} WPM)",
            'tip': "Increase pace for better engagement"
        })
        severity_score += (100 - pace_wpm) / 10

    if avg_confidence < 0.7:
        issues.append({
            'type': 'low-confidence',
            'description': "Low transcription confidence - may be unclear",
            'tip': "Speak more clearly and enunciate"
        })
        severity_score += (0.7 - avg_confidence) * 10

    # Determine severity
    if not issues:
        severity = 'good'
    elif severity_score > 5:
        severity = 'error'
    else:
        severity = 'warning'

    # Determine if exemplary (for good segments)
    is_exemplary = (
        severity == 'good' and
        140 <= pace_wpm <= 180 and
        avg_confidence > 0.9 and
        word_count >= 5
    )

    # Quality score (for good segments)
    quality_score = 0
    if severity == 'good':
        # Prefer segments with good pace
        if 140 <= pace_wpm <= 160:
            quality_score += 10
        # Prefer high confidence
        quality_score += avg_confidence * 10
        # Prefer reasonable length
        if 5 <= word_count <= 15:
            quality_score += 5

    # Primary issue
    primary_issue = issues[0] if issues else None

    return {
        'severity': severity,
        'severity_score': severity_score,
        'quality_score': quality_score,
        'is_exemplary': is_exemplary,
        'issues': issues,
        'primary_issue': primary_issue,
        'metrics': {
            'pace_wpm': round(pace_wpm, 1),
            'filler_ratio': round(filler_ratio, 3),
            'confidence': round(avg_confidence, 3)
        }
    }


def extract_segment_audio(
    audio_path: str,
    start_time: float,
    end_time: float,
    output_path: str
) -> str:
    """
    Extract audio segment from original file.

    Args:
        audio_path: Path to original audio file
        start_time: Segment start time in seconds
        end_time: Segment end time in seconds
        output_path: Path to save extracted segment

    Returns:
        Path to extracted audio file
    """
    # Load audio
    audio, sr = librosa.load(audio_path, sr=None, mono=True)

    # Calculate sample indices
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)

    # Extract segment
    segment_audio = audio[start_sample:end_sample]

    # Save
    sf.write(output_path, segment_audio, sr)

    return output_path


def generate_improved_audio(
    text: str,
    issues: List[Dict],
    output_path: str,
    voice_id: str,
    api_key: Optional[str] = None
) -> str:
    """
    Generate improved audio using ElevenLabs.

    Args:
        text: Segment text
        issues: List of issues found in segment
        output_path: Path to save improved audio
        voice_id: ElevenLabs voice ID (required - either from cloning or env)
        api_key: ElevenLabs API key (from env if not provided)

    Returns:
        Path to generated audio file
    """
    api_key = api_key or os.getenv('ELEVENLABS_API_KEY')

    if not voice_id:
        raise ValueError("voice_id must be provided")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY must be set")

    # Create improved text with adjustments based on issues
    improved_text = create_improved_ssml(text, issues)

    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=api_key)

    # Generate audio
    response = client.text_to_speech.convert(
        voice_id=voice_id,
        text=improved_text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
    )

    # Save audio
    with open(output_path, 'wb') as f:
        for chunk in response:
            f.write(chunk)

    return output_path


def create_improved_ssml(text: str, issues: List[Dict]) -> str:
    """
    Create improved text with SSML-like hints for better delivery.

    Args:
        text: Original text
        issues: List of issues to address

    Returns:
        Improved text
    """
    # For now, just return cleaned text
    # Remove filler words
    filler_words = ['um', 'uh', 'like you know', 'you know', 'so um', 'actually']
    improved = text

    for filler in filler_words:
        # Case insensitive replacement
        import re
        improved = re.sub(r'\b' + re.escape(filler) + r'\b', '', improved, flags=re.IGNORECASE)

    # Clean up multiple spaces
    improved = re.sub(r'\s+', ' ', improved).strip()

    # Add pauses for better pacing if too fast
    has_pace_issue = any(i['type'] == 'too-fast' for i in issues)
    if has_pace_issue:
        # Add commas for natural pauses
        improved = improved.replace(' and ', ', and ')
        improved = improved.replace(' but ', ', but ')

    return improved


def get_voice_id_for_segment(
    segment: Dict,
    voice_mapping: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Get the voice ID to use for a segment.

    Priority:
    1. Environment variable ELEVENLABS_VOICE_ID (if set)
    2. Voice mapping for the segment's speaker (if available)

    Args:
        segment: Segment dictionary (may contain speaker info)
        voice_mapping: Optional mapping of speaker labels to voice IDs

    Returns:
        Voice ID or None if not available
    """
    # First check environment variable
    env_voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    if env_voice_id:
        return env_voice_id

    # Then check voice mapping for speaker
    if voice_mapping:
        # Try to get speaker from segment's words
        words = segment.get('words', [])
        if words:
            # Get speaker from first word if available
            speaker = words[0].get('speaker_label')
            if speaker and speaker in voice_mapping:
                return voice_mapping[speaker]

        # If no speaker in words, use first available voice
        if voice_mapping:
            return list(voice_mapping.values())[0]

    return None


def generate_segments_with_audio(
    audio_path: str,
    coaching_analysis_path: str,
    output_dir: str,
    max_segments: int = 6,
    voice_mapping: Optional[Dict[str, str]] = None
) -> List[Dict]:
    """
    Generate segments with original and improved audio.

    Args:
        audio_path: Path to original audio file
        coaching_analysis_path: Path to coaching analysis JSON
        output_dir: Directory to save segment audio files
        max_segments: Maximum number of segments
        voice_mapping: Optional mapping of speaker labels to cloned voice IDs

    Returns:
        List of segment dictionaries with audio paths
    """
    # Load analysis
    with open(coaching_analysis_path, 'r') as f:
        analysis = json.load(f)

    # Select segments
    segments = select_interesting_segments(analysis, max_segments)

    # Create output directories
    original_dir = os.path.join(output_dir, 'original')
    improved_dir = os.path.join(output_dir, 'improved')
    os.makedirs(original_dir, exist_ok=True)
    os.makedirs(improved_dir, exist_ok=True)

    # Process each segment
    for segment in segments:
        segment_id = segment['segment_id']

        # Extract original audio
        original_path = os.path.join(original_dir, f'segment_{segment_id}.wav')
        extract_segment_audio(
            audio_path=audio_path,
            start_time=segment['start_time'],
            end_time=segment['end_time'],
            output_path=original_path
        )
        segment['original_audio_path'] = original_path

        # Get voice ID for this segment
        voice_id = get_voice_id_for_segment(segment, voice_mapping)

        # Generate improved audio
        if voice_id:
            try:
                improved_path = os.path.join(improved_dir, f'segment_{segment_id}.wav')
                generate_improved_audio(
                    text=segment['text'],
                    issues=segment['issues'],
                    output_path=improved_path,
                    voice_id=voice_id
                )
                segment['improved_audio_path'] = improved_path
            except Exception as e:
                print(f"Warning: Could not generate improved audio for segment {segment_id}: {e}")
                segment['improved_audio_path'] = None
        else:
            print(f"Warning: No voice ID available for segment {segment_id}, skipping improved audio")
            segment['improved_audio_path'] = None

    return segments


def generate_segments_with_audio_intelligent(
    audio_path: str,
    coaching_analysis_path: str,
    coaching_feedback: str,
    output_dir: str,
    max_segments: int = 6,
    voice_mapping: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None
) -> List[Dict]:
    """
    Generate segments with original and improved audio using Claude for intelligent selection.

    This is the improved version that uses Claude to select pedagogically valuable segments
    based on the coaching analysis, rather than using rule-based heuristics.

    Args:
        audio_path: Path to original audio file
        coaching_analysis_path: Path to coaching analysis JSON
        coaching_feedback: Text of coaching feedback from Claude
        output_dir: Directory to save segment audio files
        max_segments: Maximum number of segments
        voice_mapping: Optional mapping of speaker labels to cloned voice IDs
        api_key: Optional Anthropic API key (uses env var if not provided)

    Returns:
        List of segment dictionaries with audio paths

    Example segment:
    {
        "segment_id": 1,
        "time_range": {"start": 12.5, "end": 18.3},
        "start_time": 12.5,  # Added for compatibility
        "end_time": 18.3,    # Added for compatibility
        "duration": 5.8,
        "text": "So um I think...",  # Original text
        "improved_text": "I think...",  # Improved text
        "improved_ssml": "<prosody...>",  # SSML for improved version
        "word_count": 10,
        "severity": "error",
        "issues": [...],
        "coaching_tip": "...",
        "original_audio_path": "/path/to/segment_1.wav",
        "improved_audio_path": "/path/to/segment_1_improved.wav"
    }
    """
    # Load analysis
    with open(coaching_analysis_path, 'r') as f:
        analysis = json.load(f)

    print("🤖 Using Claude to select most valuable segments...")

    # Use Claude to select segments intelligently
    selection_result = select_segments_with_claude(
        coaching_analysis=analysis,
        coaching_feedback=coaching_feedback,
        max_segments=max_segments,
        api_key=api_key
    )

    segments = selection_result['segments']
    print(f"✓ Claude selected {len(segments)} segments")
    print(f"  Summary: {selection_result.get('selection_summary', '')}")

    # Enrich with metadata
    segments = enrich_segments_with_metadata(segments, analysis)

    # Add start_time/end_time for compatibility with audio extraction
    for segment in segments:
        segment['start_time'] = segment['time_range']['start']
        segment['end_time'] = segment['time_range']['end']

    # Create output directories
    original_dir = os.path.join(output_dir, 'original')
    improved_dir = os.path.join(output_dir, 'improved')
    os.makedirs(original_dir, exist_ok=True)
    os.makedirs(improved_dir, exist_ok=True)

    # Process each segment
    for segment in segments:
        segment_id = segment['segment_id']

        # Extract original audio
        original_path = os.path.join(original_dir, f'segment_{segment_id}.wav')
        extract_segment_audio(
            audio_path=audio_path,
            start_time=segment['start_time'],
            end_time=segment['end_time'],
            output_path=original_path
        )
        segment['original_audio_path'] = original_path

        # Get voice ID for this segment
        voice_id = get_voice_id_for_segment(segment, voice_mapping)

        # Generate improved audio using Claude's improved text/SSML
        if voice_id:
            try:
                improved_path = os.path.join(improved_dir, f'segment_{segment_id}.wav')

                # Use improved_ssml if available, otherwise fall back to improved_text
                improved_content = segment.get('improved_ssml')

                generate_improved_audio_from_ssml(
                    content=improved_content,
                    output_path=improved_path,
                    voice_id=voice_id
                )
                segment['improved_audio_path'] = improved_path
            except Exception as e:
                print(f"Warning: Could not generate improved audio for segment {segment_id}: {e}")
                segment['improved_audio_path'] = None
        else:
            print(f"Warning: No voice ID available for segment {segment_id}, skipping improved audio")
            segment['improved_audio_path'] = None

    return segments


def generate_improved_audio_from_ssml(
    content: str,
    output_path: str,
    voice_id: str,
    api_key: Optional[str] = None
) -> str:
    """
    Generate improved audio from SSML or plain text using ElevenLabs.

    Args:
        content: SSML markup or plain text
        output_path: Path to save improved audio
        voice_id: ElevenLabs voice ID
        api_key: ElevenLabs API key (from env if not provided)

    Returns:
        Path to generated audio file
    """
    api_key = api_key or os.getenv('ELEVENLABS_API_KEY')

    if not voice_id:
        raise ValueError("voice_id must be provided")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY must be set")

    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=api_key)

    print(f"Generating improved audio with ElevenLabs voice ID {voice_id} and content: {content[:60]}...")
    # Generate audio (ElevenLabs supports SSML-like tags)
    response = client.text_to_speech.convert(
        voice_id=voice_id,
        text=content,
        model_id="eleven_v3",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.1,
        )
    )

    # Save audio
    with open(output_path, 'wb') as f:
        for chunk in response:
            f.write(chunk)

    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python segment_generator.py <audio.wav> <coaching_analysis.json> <output_dir>")
        sys.exit(1)

    audio_path = sys.argv[1]
    analysis_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'segments_output'

    segments = generate_segments_with_audio(audio_path, analysis_path, output_dir)

    print("\n" + "=" * 80)
    print(f"GENERATED {len(segments)} SEGMENTS")
    print("=" * 80)

    for seg in segments:
        print(f"\nSegment {seg['segment_id']}: {seg['text'][:50]}...")
        print(f"  Time: {seg['start_time']:.1f}s - {seg['end_time']:.1f}s")
        print(f"  Severity: {seg['severity']}")
        if seg['primary_issue']:
            print(f"  Issue: {seg['primary_issue']['description']}")
        print(f"  Original: {seg['original_audio_path']}")
        print(f"  Improved: {seg['improved_audio_path']}")
