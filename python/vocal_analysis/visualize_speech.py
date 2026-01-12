"""
Speech visualization module for generating graphs and spectrograms.
Generates visual representations of pitch, intensity, and spectrograms for coaching feedback.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path


def generate_spectrogram(audio_path, output_path):
    """
    Generate a spectrogram visualization showing frequency content over time.
    """
    try:
        import librosa
        import librosa.display
    except ImportError:
        print("Installing librosa...")
        import subprocess
        subprocess.check_call(["pip", "install", "librosa"])
        import librosa
        import librosa.display

    y, sr = librosa.load(str(audio_path))

    # Generate mel spectrogram
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)

    # Create figure
    plt.figure(figsize=(14, 6))
    librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel', fmax=8000)
    plt.colorbar(format='%+2.0f dB')
    plt.title('Mel Spectrogram - Frequency Content Over Time', fontsize=14, fontweight='bold')
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Frequency (Hz)', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Spectrogram saved to: {output_path}")


def generate_pitch_plot(coaching_data, output_path):
    """
    Generate pitch (F0) contour visualization over time.
    """
    pitch_contour = coaching_data['acoustic_features']['parselmouth']['pitch_contour']

    if not pitch_contour:
        print("  ⚠ No pitch data available")
        return

    times = [p['time'] for p in pitch_contour]
    pitches = [p['pitch_hz'] for p in pitch_contour]

    pitch_mean = coaching_data['acoustic_features']['parselmouth']['pitch_mean_hz']
    pitch_std = coaching_data['acoustic_features']['parselmouth']['pitch_std_hz']

    plt.figure(figsize=(14, 5))
    plt.plot(times, pitches, linewidth=1.5, color='#2E86AB', alpha=0.8)

    # Add mean line
    plt.axhline(y=pitch_mean, color='red', linestyle='--', linewidth=1,
                label=f'Mean: {pitch_mean:.1f} Hz', alpha=0.7)

    # Add std bands
    plt.fill_between([times[0], times[-1]],
                     [pitch_mean - pitch_std] * 2,
                     [pitch_mean + pitch_std] * 2,
                     alpha=0.2, color='red', label=f'±1 SD: {pitch_std:.1f} Hz')

    plt.title('Pitch (F0) Contour - Voice Intonation Over Time', fontsize=14, fontweight='bold')
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Pitch (Hz)', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Pitch plot saved to: {output_path}")


def generate_intensity_plot(coaching_data, output_path):
    """
    Generate intensity (loudness) visualization over time.
    """
    intensity_contour = coaching_data['acoustic_features']['parselmouth']['intensity_contour']

    if not intensity_contour:
        print("  ⚠ No intensity data available")
        return

    times = [i['time'] for i in intensity_contour]
    intensities = [i['intensity_db'] for i in intensity_contour]

    intensity_mean = coaching_data['acoustic_features']['parselmouth']['intensity_mean_db']
    intensity_std = coaching_data['acoustic_features']['parselmouth']['intensity_std_db']

    plt.figure(figsize=(14, 5))
    plt.plot(times, intensities, linewidth=1.5, color='#A23B72', alpha=0.8)

    # Add mean line
    plt.axhline(y=intensity_mean, color='green', linestyle='--', linewidth=1,
                label=f'Mean: {intensity_mean:.1f} dB', alpha=0.7)

    # Add std bands
    plt.fill_between([times[0], times[-1]],
                     [intensity_mean - intensity_std] * 2,
                     [intensity_mean + intensity_std] * 2,
                     alpha=0.2, color='green', label=f'±1 SD: {intensity_std:.1f} dB')

    plt.title('Intensity (Loudness) - Voice Volume Over Time', fontsize=14, fontweight='bold')
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Intensity (dB)', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Intensity plot saved to: {output_path}")


def generate_combined_plot(coaching_data, output_path):
    """
    Generate a combined visualization with pitch and intensity on same timeline.
    """
    pitch_contour = coaching_data['acoustic_features']['parselmouth']['pitch_contour']
    intensity_contour = coaching_data['acoustic_features']['parselmouth']['intensity_contour']

    if not pitch_contour or not intensity_contour:
        print("  ⚠ Missing pitch or intensity data")
        return

    pitch_times = [p['time'] for p in pitch_contour]
    pitches = [p['pitch_hz'] for p in pitch_contour]

    intensity_times = [i['time'] for i in intensity_contour]
    intensities = [i['intensity_db'] for i in intensity_contour]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Pitch plot
    ax1.plot(pitch_times, pitches, linewidth=1.5, color='#2E86AB', alpha=0.8)
    ax1.set_ylabel('Pitch (Hz)', fontsize=12, fontweight='bold')
    ax1.set_title('Pitch & Intensity Analysis - Voice Characteristics Over Time',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Intensity plot
    ax2.plot(intensity_times, intensities, linewidth=1.5, color='#A23B72', alpha=0.8)
    ax2.set_xlabel('Time (seconds)', fontsize=12)
    ax2.set_ylabel('Intensity (dB)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Combined plot saved to: {output_path}")


def generate_speech_metrics_chart(coaching_data, output_path):
    """
    Generate a bar chart showing key speech metrics.
    """
    metrics = coaching_data['speech_metrics']

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

    # Speaking rate
    ax1.bar(['Speaking Rate'], [metrics['speaking_rate_wpm']], color='#2E86AB', width=0.5)
    ax1.axhline(y=150, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Normal (150 WPM)')
    ax1.set_ylabel('Words Per Minute', fontsize=11)
    ax1.set_title('Speaking Rate', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # Filler words
    filler_pct = metrics['filler_word_ratio'] * 100
    ax2.bar(['Filler Word %'], [filler_pct], color='#A23B72', width=0.5)
    ax2.axhline(y=5, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Target (<5%)')
    ax2.set_ylabel('Percentage (%)', fontsize=11)
    ax2.set_title(f"Filler Words ({metrics['filler_word_count']} total)", fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Pitch variation
    pitch_range = coaching_data['acoustic_features']['parselmouth']['pitch_range_hz']
    ax3.bar(['Pitch Range'], [pitch_range], color='#F18F01', width=0.5)
    ax3.axhline(y=50, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Good (>50 Hz)')
    ax3.set_ylabel('Frequency Range (Hz)', fontsize=11)
    ax3.set_title('Pitch Variation', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # Pauses
    ax4.bar(['Long Pauses'], [metrics['pause_count']], color='#6A994E', width=0.5)
    ax4.set_ylabel('Count', fontsize=11)
    ax4.set_title('Long Pauses (>0.5s)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Speech Coaching Metrics Summary', fontsize=14, fontweight='bold', y=1.0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Metrics chart saved to: {output_path}")


def generate_all_visualizations(coaching_json_path, audio_path, output_dir):
    """
    Generate all visualizations for speech coaching analysis.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load coaching data
    with open(coaching_json_path, 'r') as f:
        coaching_data = json.load(f)

    base_name = Path(coaching_json_path).stem

    print("\nGenerating visualizations...")

    # Generate all plots
    generate_spectrogram(audio_path, output_dir / f"{base_name}_spectrogram.png")
    generate_pitch_plot(coaching_data, output_dir / f"{base_name}_pitch.png")
    generate_intensity_plot(coaching_data, output_dir / f"{base_name}_intensity.png")
    generate_combined_plot(coaching_data, output_dir / f"{base_name}_combined.png")
    generate_speech_metrics_chart(coaching_data, output_dir / f"{base_name}_metrics.png")

    print(f"\n✅ All visualizations saved to: {output_dir}/")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python visualize_speech.py <coaching_analysis.json> <audio.wav> <output_dir>")
        sys.exit(1)

    coaching_json = sys.argv[1]
    audio_file = sys.argv[2]
    output_directory = sys.argv[3]

    generate_all_visualizations(coaching_json, audio_file, output_directory)
