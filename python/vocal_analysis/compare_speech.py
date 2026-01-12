"""
Speech comparison module for analyzing and visualizing differences between two speeches.
Generates comparative visualizations and metrics for coaching feedback.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path


def load_coaching_data(coaching_json_path):
    """Load coaching analysis data from JSON file."""
    with open(coaching_json_path, 'r') as f:
        return json.load(f)


def generate_side_by_side_pitch_comparison(data1, data2, label1, label2, output_path):
    """
    Generate side-by-side pitch contour comparison with word labels.
    """
    pitch_contour1 = data1['acoustic_features']['parselmouth']['pitch_contour']
    pitch_contour2 = data2['acoustic_features']['parselmouth']['pitch_contour']

    if not pitch_contour1 or not pitch_contour2:
        print("  ⚠ Missing pitch data for one or both files")
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), sharex=False)

    # Plot first speech
    times1 = [p['time'] for p in pitch_contour1]
    pitches1 = [p['pitch_hz'] for p in pitch_contour1]
    pitch_mean1 = data1['acoustic_features']['parselmouth']['pitch_mean_hz']
    pitch_std1 = data1['acoustic_features']['parselmouth']['pitch_std_hz']

    ax1.plot(times1, pitches1, linewidth=2, color='#2E86AB', alpha=0.9, label=label1)
    ax1.axhline(y=pitch_mean1, color='red', linestyle='--', linewidth=1,
                label=f'Mean: {pitch_mean1:.1f} Hz', alpha=0.7)
    ax1.fill_between([times1[0], times1[-1]],
                     [pitch_mean1 - pitch_std1] * 2,
                     [pitch_mean1 + pitch_std1] * 2,
                     alpha=0.2, color='red', label=f'±1 SD: {pitch_std1:.1f} Hz')

    # Add word labels for first speech (sampled)
    word_level1 = data1.get('word_level_analysis', [])
    if word_level1:
        total_duration1 = times1[-1] if times1 else 0
        word_interval1 = max(1, int(len(word_level1) / (total_duration1 / 2)))
        for i, word_data in enumerate(word_level1):
            if i % word_interval1 == 0 or len(word_data['word']) > 5:
                word_mid = (word_data['start_time'] + word_data['end_time']) / 2
                pitch_at_word = word_data.get('pitch_hz')
                if pitch_at_word:
                    ax1.axvspan(word_data['start_time'], word_data['end_time'],
                               alpha=0.1, color='green', zorder=0)
                    ax1.annotate(word_data['word'],
                               xy=(word_mid, pitch_at_word),
                               xytext=(0, 10),
                               textcoords='offset points',
                               fontsize=7,
                               ha='center',
                               va='bottom',
                               color='#1a5490',
                               fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.2',
                                       facecolor='white',
                                       edgecolor='#2E86AB',
                                       alpha=0.7,
                                       linewidth=0.5),
                               zorder=4)

    ax1.set_title(f'{label1} - Pitch Contour', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Pitch (Hz)', fontsize=11)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    y_range1 = max(pitches1) - min(pitches1) if pitches1 else 100
    ax1.set_ylim(min(pitches1) - y_range1 * 0.1 if pitches1 else 0,
                 max(pitches1) + y_range1 * 0.3 if pitches1 else 100)

    # Plot second speech
    times2 = [p['time'] for p in pitch_contour2]
    pitches2 = [p['pitch_hz'] for p in pitch_contour2]
    pitch_mean2 = data2['acoustic_features']['parselmouth']['pitch_mean_hz']
    pitch_std2 = data2['acoustic_features']['parselmouth']['pitch_std_hz']

    ax2.plot(times2, pitches2, linewidth=2, color='#A23B72', alpha=0.9, label=label2)
    ax2.axhline(y=pitch_mean2, color='red', linestyle='--', linewidth=1,
                label=f'Mean: {pitch_mean2:.1f} Hz', alpha=0.7)
    ax2.fill_between([times2[0], times2[-1]],
                     [pitch_mean2 - pitch_std2] * 2,
                     [pitch_mean2 + pitch_std2] * 2,
                     alpha=0.2, color='red', label=f'±1 SD: {pitch_std2:.1f} Hz')

    # Add word labels for second speech (sampled)
    word_level2 = data2.get('word_level_analysis', [])
    if word_level2:
        total_duration2 = times2[-1] if times2 else 0
        word_interval2 = max(1, int(len(word_level2) / (total_duration2 / 2)))
        for i, word_data in enumerate(word_level2):
            if i % word_interval2 == 0 or len(word_data['word']) > 5:
                word_mid = (word_data['start_time'] + word_data['end_time']) / 2
                pitch_at_word = word_data.get('pitch_hz')
                if pitch_at_word:
                    ax2.axvspan(word_data['start_time'], word_data['end_time'],
                               alpha=0.1, color='green', zorder=0)
                    ax2.annotate(word_data['word'],
                               xy=(word_mid, pitch_at_word),
                               xytext=(0, 10),
                               textcoords='offset points',
                               fontsize=7,
                               ha='center',
                               va='bottom',
                               color='#8b1a5e',
                               fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.2',
                                       facecolor='white',
                                       edgecolor='#A23B72',
                                       alpha=0.7,
                                       linewidth=0.5),
                               zorder=4)

    ax2.set_title(f'{label2} - Pitch Contour', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Time (seconds)', fontsize=11)
    ax2.set_ylabel('Pitch (Hz)', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    y_range2 = max(pitches2) - min(pitches2) if pitches2 else 100
    ax2.set_ylim(min(pitches2) - y_range2 * 0.1 if pitches2 else 0,
                 max(pitches2) + y_range2 * 0.3 if pitches2 else 100)

    plt.suptitle('Side-by-Side Pitch Comparison', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Side-by-side pitch comparison saved to: {output_path}")


def generate_overlaid_pitch_comparison(data1, data2, label1, label2, output_path):
    """
    Generate overlaid pitch contours for direct comparison.
    """
    pitch_contour1 = data1['acoustic_features']['parselmouth']['pitch_contour']
    pitch_contour2 = data2['acoustic_features']['parselmouth']['pitch_contour']

    if not pitch_contour1 or not pitch_contour2:
        print("  ⚠ Missing pitch data for one or both files")
        return

    times1 = [p['time'] for p in pitch_contour1]
    pitches1 = [p['pitch_hz'] for p in pitch_contour1]
    pitch_mean1 = data1['acoustic_features']['parselmouth']['pitch_mean_hz']

    times2 = [p['time'] for p in pitch_contour2]
    pitches2 = [p['pitch_hz'] for p in pitch_contour2]
    pitch_mean2 = data2['acoustic_features']['parselmouth']['pitch_mean_hz']

    fig, ax = plt.subplots(figsize=(18, 7))

    # Plot both pitch contours
    ax.plot(times1, pitches1, linewidth=2, color='#2E86AB', alpha=0.8,
            label=f'{label1} (Mean: {pitch_mean1:.1f} Hz)')
    ax.plot(times2, pitches2, linewidth=2, color='#A23B72', alpha=0.8,
            label=f'{label2} (Mean: {pitch_mean2:.1f} Hz)')

    # Add mean lines
    ax.axhline(y=pitch_mean1, color='#2E86AB', linestyle='--', linewidth=1, alpha=0.5)
    ax.axhline(y=pitch_mean2, color='#A23B72', linestyle='--', linewidth=1, alpha=0.5)

    ax.set_title('Overlaid Pitch Comparison', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Pitch (Hz)', fontsize=12)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Overlaid pitch comparison saved to: {output_path}")


def generate_metrics_comparison_bars(data1, data2, label1, label2, output_path):
    """
    Generate bar chart comparing key speech metrics between two speeches.
    """
    metrics1 = data1['speech_metrics']
    metrics2 = data2['speech_metrics']
    acoustic1 = data1['acoustic_features']['parselmouth']
    acoustic2 = data2['acoustic_features']['parselmouth']

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    # Speaking Rate
    ax = axes[0]
    bars = ax.bar([label1, label2],
                   [metrics1['speaking_rate_wpm'], metrics2['speaking_rate_wpm']],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.axhline(y=150, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Normal (150 WPM)')
    ax.set_ylabel('Words Per Minute', fontsize=10)
    ax.set_title('Speaking Rate', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Filler Word Ratio
    ax = axes[1]
    filler1 = metrics1['filler_word_ratio'] * 100
    filler2 = metrics2['filler_word_ratio'] * 100
    bars = ax.bar([label1, label2], [filler1, filler2],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.axhline(y=5, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Target (<5%)')
    ax.set_ylabel('Percentage (%)', fontsize=10)
    ax.set_title(f'Filler Words', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Pitch Range
    ax = axes[2]
    bars = ax.bar([label1, label2],
                   [acoustic1['pitch_range_hz'], acoustic2['pitch_range_hz']],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.axhline(y=50, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Good (>50 Hz)')
    ax.set_ylabel('Frequency (Hz)', fontsize=10)
    ax.set_title('Pitch Variation', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Pause Count
    ax = axes[3]
    bars = ax.bar([label1, label2],
                   [metrics1['pause_count'], metrics2['pause_count']],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.set_ylabel('Count', fontsize=10)
    ax.set_title('Long Pauses (>0.5s)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Intensity Range
    ax = axes[4]
    bars = ax.bar([label1, label2],
                   [acoustic1['intensity_range_db'], acoustic2['intensity_range_db']],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.axhline(y=10, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Varied (>10 dB)')
    ax.set_ylabel('Decibels (dB)', fontsize=10)
    ax.set_title('Volume Variation', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Voice Quality (HNR)
    ax = axes[5]
    bars = ax.bar([label1, label2],
                   [acoustic1['harmonics_to_noise_ratio_mean_db'],
                    acoustic2['harmonics_to_noise_ratio_mean_db']],
                   color=['#2E86AB', '#A23B72'], width=0.6)
    ax.axhline(y=10, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Good (>10 dB)')
    ax.set_ylabel('Decibels (dB)', fontsize=10)
    ax.set_title('Voice Quality (HNR)', fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.suptitle('Speech Metrics Comparison', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Metrics comparison bars saved to: {output_path}")


def generate_comparison_summary_table(data1, data2, label1, label2, output_path):
    """
    Generate a detailed comparison table visualization.
    """
    metrics1 = data1['speech_metrics']
    metrics2 = data2['speech_metrics']
    acoustic1 = data1['acoustic_features']['parselmouth']
    acoustic2 = data2['acoustic_features']['parselmouth']

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.axis('tight')
    ax.axis('off')

    # Determine better values with clear indicators
    def get_better_indicator(is_first_better):
        """Return label1 or label2 to indicate which is better."""
        if is_first_better is None:
            return '-'
        return label1 if is_first_better else label2

    # Calculate which is better for each metric
    speaking_rate_better = abs(metrics1['speaking_rate_wpm'] - 150) < abs(metrics2['speaking_rate_wpm'] - 150)
    total_words_better = metrics1['total_words'] > metrics2['total_words']
    filler_better = metrics1['filler_word_ratio'] < metrics2['filler_word_ratio']
    pauses_better = metrics1['pause_count'] < metrics2['pause_count']
    pitch_range_better = acoustic1['pitch_range_hz'] > acoustic2['pitch_range_hz']
    intensity_range_better = acoustic1['intensity_range_db'] > acoustic2['intensity_range_db']
    hnr_better = acoustic1['harmonics_to_noise_ratio_mean_db'] > acoustic2['harmonics_to_noise_ratio_mean_db']

    # Prepare table data
    table_data = [
        ['Metric', label1, label2, 'Difference', 'Winner'],
        ['', '', '', '', ''],
        ['Speaking Rate (WPM)',
         f"{metrics1['speaking_rate_wpm']:.1f}",
         f"{metrics2['speaking_rate_wpm']:.1f}",
         f"{abs(metrics1['speaking_rate_wpm'] - metrics2['speaking_rate_wpm']):.1f}",
         get_better_indicator(speaking_rate_better)],

        ['Total Words',
         f"{metrics1['total_words']}",
         f"{metrics2['total_words']}",
         f"{abs(metrics1['total_words'] - metrics2['total_words'])}",
         get_better_indicator(total_words_better)],

        ['Filler Words (%)',
         f"{metrics1['filler_word_ratio']*100:.2f}",
         f"{metrics2['filler_word_ratio']*100:.2f}",
         f"{abs(metrics1['filler_word_ratio'] - metrics2['filler_word_ratio'])*100:.2f}",
         get_better_indicator(filler_better)],

        ['Long Pauses (>0.5s)',
         f"{metrics1['pause_count']}",
         f"{metrics2['pause_count']}",
         f"{abs(metrics1['pause_count'] - metrics2['pause_count'])}",
         get_better_indicator(pauses_better)],

        ['', '', '', '', ''],
        ['Pitch Mean (Hz)',
         f"{acoustic1['pitch_mean_hz']:.1f}",
         f"{acoustic2['pitch_mean_hz']:.1f}",
         f"{abs(acoustic1['pitch_mean_hz'] - acoustic2['pitch_mean_hz']):.1f}",
         '-'],

        ['Pitch Range (Hz)',
         f"{acoustic1['pitch_range_hz']:.1f}",
         f"{acoustic2['pitch_range_hz']:.1f}",
         f"{abs(acoustic1['pitch_range_hz'] - acoustic2['pitch_range_hz']):.1f}",
         get_better_indicator(pitch_range_better)],

        ['Intensity Mean (dB)',
         f"{acoustic1['intensity_mean_db']:.1f}",
         f"{acoustic2['intensity_mean_db']:.1f}",
         f"{abs(acoustic1['intensity_mean_db'] - acoustic2['intensity_mean_db']):.1f}",
         '-'],

        ['Intensity Range (dB)',
         f"{acoustic1['intensity_range_db']:.1f}",
         f"{acoustic2['intensity_range_db']:.1f}",
         f"{abs(acoustic1['intensity_range_db'] - acoustic2['intensity_range_db']):.1f}",
         get_better_indicator(intensity_range_better)],

        ['Voice Quality (HNR dB)',
         f"{acoustic1['harmonics_to_noise_ratio_mean_db']:.1f}",
         f"{acoustic2['harmonics_to_noise_ratio_mean_db']:.1f}",
         f"{abs(acoustic1['harmonics_to_noise_ratio_mean_db'] - acoustic2['harmonics_to_noise_ratio_mean_db']):.1f}",
         get_better_indicator(hnr_better)],

        ['', '', '', '', ''],
        ['Speech Duration (s)',
         f"{metrics1['speech_duration_seconds']:.1f}",
         f"{metrics2['speech_duration_seconds']:.1f}",
         f"{abs(metrics1['speech_duration_seconds'] - metrics2['speech_duration_seconds']):.1f}",
         '-'],
    ]

    # Create table
    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.35, 0.15, 0.15, 0.15, 0.1])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Style header row
    for i in range(5):
        cell = table[(0, i)]
        cell.set_facecolor('#2E86AB')
        cell.set_text_props(weight='bold', color='white', fontsize=11)

    # Style data rows
    for i in range(2, len(table_data)):
        if table_data[i][0] == '':  # Separator rows
            for j in range(5):
                table[(i, j)].set_facecolor('#f0f0f0')
        else:
            for j in range(5):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#ffffff')
                else:
                    cell.set_facecolor('#f9f9f9')

                # Highlight "Winner" column - all winners get green
                if j == 4 and table_data[i][4] not in ['-', '']:
                    cell.set_facecolor('#c8e6c9')  # Light green for all winners
                    cell.set_text_props(weight='bold', color='#2e7d32', fontsize=10)

                # Also highlight the winner's value in the corresponding data column
                if table_data[i][4] == label1 and j == 1:  # Highlight label1 column if winner
                    cell.set_text_props(weight='bold', color='#2e7d32', fontsize=10)
                elif table_data[i][4] == label2 and j == 2:  # Highlight label2 column if winner
                    cell.set_text_props(weight='bold', color='#2e7d32', fontsize=10)

    plt.title('Detailed Metrics Comparison Table', fontsize=14, fontweight='bold', pad=20)
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Comparison summary table saved to: {output_path}")


def generate_normalized_pitch_comparison(data1, data2, label1, label2, output_path):
    """
    Generate normalized pitch comparison (shows relative pitch changes from mean).
    This is useful for comparing pitch patterns independent of speaker's baseline pitch.
    """
    pitch_contour1 = data1['acoustic_features']['parselmouth']['pitch_contour']
    pitch_contour2 = data2['acoustic_features']['parselmouth']['pitch_contour']

    if not pitch_contour1 or not pitch_contour2:
        print("  ⚠ Missing pitch data for one or both files")
        return

    times1 = [p['time'] for p in pitch_contour1]
    pitches1 = [p['pitch_hz'] for p in pitch_contour1]
    pitch_mean1 = data1['acoustic_features']['parselmouth']['pitch_mean_hz']
    normalized_pitches1 = [(p - pitch_mean1) for p in pitches1]

    times2 = [p['time'] for p in pitch_contour2]
    pitches2 = [p['pitch_hz'] for p in pitch_contour2]
    pitch_mean2 = data2['acoustic_features']['parselmouth']['pitch_mean_hz']
    normalized_pitches2 = [(p - pitch_mean2) for p in pitches2]

    fig, ax = plt.subplots(figsize=(18, 7))

    # Plot normalized pitch contours
    ax.plot(times1, normalized_pitches1, linewidth=2, color='#2E86AB', alpha=0.8, label=label1)
    ax.plot(times2, normalized_pitches2, linewidth=2, color='#A23B72', alpha=0.8, label=label2)

    # Add zero line (mean pitch)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3, label='Mean Pitch')

    ax.set_title('Normalized Pitch Comparison (Relative to Mean)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Pitch Deviation from Mean (Hz)', fontsize=12)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Normalized pitch comparison saved to: {output_path}")


def compare_speeches(coaching_json_path1, coaching_json_path2, output_dir, label1=None, label2=None):
    """
    Main function to compare two speeches and generate all comparison visualizations.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nLoading coaching data...")
    data1 = load_coaching_data(coaching_json_path1)
    data2 = load_coaching_data(coaching_json_path2)

    # Generate labels from filenames if not provided
    if not label1:
        label1 = Path(coaching_json_path1).stem.replace('_coaching', '')
    if not label2:
        label2 = Path(coaching_json_path2).stem.replace('_coaching', '')

    print(f"\nComparing: '{label1}' vs '{label2}'")
    print("\nGenerating comparison visualizations...")

    # Generate all comparison visualizations
    generate_side_by_side_pitch_comparison(
        data1, data2, label1, label2,
        output_dir / "comparison_pitch_sidebyside.svg"
    )

    generate_overlaid_pitch_comparison(
        data1, data2, label1, label2,
        output_dir / "comparison_pitch_overlaid.svg"
    )

    generate_normalized_pitch_comparison(
        data1, data2, label1, label2,
        output_dir / "comparison_pitch_normalized.svg"
    )

    generate_metrics_comparison_bars(
        data1, data2, label1, label2,
        output_dir / "comparison_metrics_bars.svg"
    )

    generate_comparison_summary_table(
        data1, data2, label1, label2,
        output_dir / "comparison_summary_table.svg"
    )

    print(f"\n✅ All comparison visualizations saved to: {output_dir}/")
    print("\nGenerated files:")
    print("  - comparison_pitch_sidebyside.svg (side-by-side pitch with words)")
    print("  - comparison_pitch_overlaid.svg (overlaid pitch contours)")
    print("  - comparison_pitch_normalized.svg (normalized pitch patterns)")
    print("  - comparison_metrics_bars.svg (bar chart comparison)")
    print("  - comparison_summary_table.svg (detailed metrics table)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python compare_speech.py <coaching1.json> <coaching2.json> <output_dir> [label1] [label2]")
        sys.exit(1)

    coaching_json1 = sys.argv[1]
    coaching_json2 = sys.argv[2]
    output_directory = sys.argv[3]

    label1 = sys.argv[4] if len(sys.argv) > 4 else None
    label2 = sys.argv[5] if len(sys.argv) > 5 else None

    compare_speeches(coaching_json1, coaching_json2, output_directory, label1, label2)
