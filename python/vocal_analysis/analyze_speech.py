"""
Speech analysis module for coaching - extracts acoustic features from audio.
Uses Parselmouth (Praat) for phonetic analysis and librosa for general audio analysis.
"""

import json
import numpy as np
from pathlib import Path


def analyze_audio_with_parselmouth(audio_path):
    """
    Extract acoustic features using Parselmouth (Praat).
    Returns pitch, intensity, formants, and voice quality metrics.
    """
    try:
        import parselmouth
        from parselmouth.praat import call
    except ImportError:
        print("Installing parselmouth...")
        import subprocess
        subprocess.check_call(["pip", "install", "praat-parselmouth"])
        import parselmouth
        from parselmouth.praat import call

    sound = parselmouth.Sound(str(audio_path))

    # Extract pitch (F0)
    pitch = call(sound, "To Pitch", 0.0, 75, 600)  # 75-600 Hz range for speech
    pitch_values = pitch.selected_array['frequency']
    pitch_values = pitch_values[pitch_values > 0]  # Remove unvoiced frames

    # Extract intensity (loudness)
    intensity = call(sound, "To Intensity", 75, 0.0, True)
    intensity_values = intensity.values[0]
    intensity_values = intensity_values[intensity_values > 0]

    # Extract formants (vowel quality)
    formant = call(sound, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)

    # Get time-series data for alignment with transcript
    pitch_times = pitch.xs()
    intensity_times = intensity.xs()

    # Extract pitch contour with timestamps
    pitch_contour = []
    for i, time in enumerate(pitch_times):
        freq = call(pitch, "Get value at time", time, "Hertz", "Linear")
        if freq and not np.isnan(freq):
            pitch_contour.append({"time": float(time), "pitch_hz": float(freq)})

    # Extract intensity contour with timestamps
    intensity_contour = []
    for i, time in enumerate(intensity_times):
        db = call(intensity, "Get value at time", time, "Cubic")
        if db and not np.isnan(db):
            intensity_contour.append({"time": float(time), "intensity_db": float(db)})

    # Calculate voice quality metrics
    harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
    hnr_values = harmonicity.values[0]
    hnr_values = hnr_values[~np.isnan(hnr_values)]

    # Get formant values at midpoint
    mid_time = sound.duration / 2
    f1 = call(formant, "Get value at time", 1, mid_time, "Hertz", "Linear")
    f2 = call(formant, "Get value at time", 2, mid_time, "Hertz", "Linear")
    f3 = call(formant, "Get value at time", 3, mid_time, "Hertz", "Linear")

    return {
        "pitch_mean_hz": float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0,
        "pitch_std_hz": float(np.std(pitch_values)) if len(pitch_values) > 0 else 0,
        "pitch_min_hz": float(np.min(pitch_values)) if len(pitch_values) > 0 else 0,
        "pitch_max_hz": float(np.max(pitch_values)) if len(pitch_values) > 0 else 0,
        "pitch_range_hz": float(np.max(pitch_values) - np.min(pitch_values)) if len(pitch_values) > 0 else 0,
        "pitch_contour": pitch_contour,

        "intensity_mean_db": float(np.mean(intensity_values)) if len(intensity_values) > 0 else 0,
        "intensity_std_db": float(np.std(intensity_values)) if len(intensity_values) > 0 else 0,
        "intensity_range_db": float(np.max(intensity_values) - np.min(intensity_values)) if len(intensity_values) > 0 else 0,
        "intensity_contour": intensity_contour,

        "harmonics_to_noise_ratio_mean_db": float(np.mean(hnr_values)) if len(hnr_values) > 0 else 0,

        "formant_f1_hz": float(f1) if f1 and not np.isnan(f1) else 0,
        "formant_f2_hz": float(f2) if f2 and not np.isnan(f2) else 0,
        "formant_f3_hz": float(f3) if f3 and not np.isnan(f3) else 0,

        "duration_seconds": float(sound.duration)
    }


def analyze_audio_with_librosa(audio_path):
    """
    Extract audio features using librosa for rhythm and tempo analysis.
    """
    try:
        import librosa
    except ImportError:
        print("Installing librosa...")
        import subprocess
        subprocess.check_call(["pip", "install", "librosa"])
        import librosa

    y, sr = librosa.load(str(audio_path))

    # Detect speaking rate (tempo)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    # RMS energy (volume variation)
    rms = librosa.feature.rms(y=y)[0]

    # Zero crossing rate (voice quality indicator)
    zcr = librosa.feature.zero_crossing_rate(y)[0]

    return {
        "tempo_bpm": float(tempo),
        "rms_energy_mean": float(np.mean(rms)),
        "rms_energy_std": float(np.std(rms)),
        "zero_crossing_rate_mean": float(np.mean(zcr)),
        "duration_seconds": float(librosa.get_duration(y=y, sr=sr))
    }


def calculate_speech_metrics(transcript_data, acoustic_features):
    """
    Calculate speech coaching metrics by combining transcript and acoustic data.
    """
    items = transcript_data['results']['items']

    # Count pronunciation items (words)
    words = [item for item in items if item['type'] == 'pronunciation']
    total_words = len(words)

    # Calculate speech duration
    if total_words > 0:
        start_time = float(words[0]['start_time'])
        end_time = float(words[-1]['end_time'])
        speech_duration = end_time - start_time
    else:
        speech_duration = 0

    # Calculate speaking rate
    speaking_rate_wpm = (total_words / speech_duration * 60) if speech_duration > 0 else 0

    # Detect filler words
    filler_words = ['uh', 'um', 'ah', 'er', 'like', 'you know', 'actually', 'basically']
    filler_count = sum(1 for word in words if word['alternatives'][0]['content'].lower() in filler_words)

    # Calculate pauses (gaps > 0.5s between words)
    pauses = []
    for i in range(len(words) - 1):
        gap = float(words[i+1]['start_time']) - float(words[i]['end_time'])
        if gap > 0.5:
            pauses.append({
                "after_word": words[i]['alternatives'][0]['content'],
                "duration_seconds": float(gap),
                "timestamp": float(words[i]['end_time'])
            })

    # Average confidence
    avg_confidence = np.mean([float(word['alternatives'][0]['confidence']) for word in words])

    return {
        "total_words": total_words,
        "speech_duration_seconds": float(speech_duration),
        "speaking_rate_wpm": float(speaking_rate_wpm),
        "filler_word_count": filler_count,
        "filler_word_ratio": float(filler_count / total_words) if total_words > 0 else 0,
        "pause_count": len(pauses),
        "pauses": pauses,
        "average_transcription_confidence": float(avg_confidence),
        "pitch_variation_assessment": "monotone" if acoustic_features['parselmouth']['pitch_range_hz'] < 50 else "varied",
        "volume_variation_assessment": "consistent" if acoustic_features['parselmouth']['intensity_range_db'] < 10 else "varied"
    }


def align_acoustic_features_with_words(transcript_data, acoustic_features):
    """
    Align pitch and intensity values with each word for detailed analysis.
    """
    items = transcript_data['results']['items']
    words = [item for item in items if item['type'] == 'pronunciation']

    pitch_contour = acoustic_features['parselmouth']['pitch_contour']
    intensity_contour = acoustic_features['parselmouth']['intensity_contour']

    word_level_features = []

    for word in words:
        word_start = float(word['start_time'])
        word_end = float(word['end_time'])
        word_mid = (word_start + word_end) / 2

        # Find pitch at word midpoint
        pitch_at_word = None
        for pitch_point in pitch_contour:
            if abs(pitch_point['time'] - word_mid) < 0.1:  # Within 100ms
                pitch_at_word = pitch_point['pitch_hz']
                break

        # Find intensity at word midpoint
        intensity_at_word = None
        for intensity_point in intensity_contour:
            if abs(intensity_point['time'] - word_mid) < 0.1:
                intensity_at_word = intensity_point['intensity_db']
                break

        word_level_features.append({
            "word": word['alternatives'][0]['content'],
            "start_time": word_start,
            "end_time": word_end,
            "confidence": float(word['alternatives'][0]['confidence']),
            "pitch_hz": pitch_at_word,
            "intensity_db": intensity_at_word
        })

    return word_level_features


def analyze_speech_for_coaching(transcript_json_path, audio_path, output_path):
    """
    Main function to analyze speech for coaching purposes.
    Combines AWS Transcribe output with acoustic analysis.
    """
    print(f"Loading transcript from {transcript_json_path}...")
    with open(transcript_json_path, 'r') as f:
        transcript_data = json.load(f)

    print(f"Analyzing audio with Parselmouth (Praat)...")
    parselmouth_features = analyze_audio_with_parselmouth(audio_path)

    print(f"Analyzing audio with librosa...")
    librosa_features = analyze_audio_with_librosa(audio_path)

    acoustic_features = {
        "parselmouth": parselmouth_features,
        "librosa": librosa_features
    }

    print(f"Calculating speech metrics...")
    speech_metrics = calculate_speech_metrics(transcript_data, acoustic_features)

    print(f"Aligning acoustic features with words...")
    word_level_features = align_acoustic_features_with_words(transcript_data, acoustic_features)

    # Combine all data
    coaching_data = {
        "metadata": {
            "transcript_file": str(transcript_json_path),
            "audio_file": str(audio_path),
            "job_name": transcript_data.get('jobName', 'N/A')
        },
        "transcript": transcript_data['results']['transcripts'][0]['transcript'],
        "speech_metrics": speech_metrics,
        "acoustic_features": acoustic_features,
        "word_level_analysis": word_level_features
    }

    # Save output
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(coaching_data, f, indent=2)

    print(f"\n✅ Analysis complete! Output saved to: {output_file}")
    print(f"\nQuick Summary:")
    print(f"  - Total words: {speech_metrics['total_words']}")
    print(f"  - Speaking rate: {speech_metrics['speaking_rate_wpm']:.1f} WPM")
    print(f"  - Filler words: {speech_metrics['filler_word_count']} ({speech_metrics['filler_word_ratio']*100:.1f}%)")
    print(f"  - Pauses (>0.5s): {speech_metrics['pause_count']}")
    print(f"  - Pitch range: {acoustic_features['parselmouth']['pitch_range_hz']:.1f} Hz ({speech_metrics['pitch_variation_assessment']})")
    print(f"  - Volume variation: {acoustic_features['parselmouth']['intensity_range_db']:.1f} dB ({speech_metrics['volume_variation_assessment']})")
    print(f"  - Voice quality (HNR): {acoustic_features['parselmouth']['harmonics_to_noise_ratio_mean_db']:.1f} dB")

    return coaching_data


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python analyze_speech.py <transcript.json> <audio.wav> <output.json>")
        sys.exit(1)

    transcript_path = sys.argv[1]
    audio_path = sys.argv[2]
    output_path = sys.argv[3]

    analyze_speech_for_coaching(transcript_path, audio_path, output_path)
