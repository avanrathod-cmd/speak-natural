#!/usr/bin/env python3
"""
Unified speech coaching pipeline.

Runs the complete workflow:
1. Analyze speech (extract acoustic features + metrics)
2. Generate AI coaching feedback (critique + improved SSML)

Note: Graph generation has been removed as the frontend uses its own waveform
visualization component and doesn't use the SVG charts.

Usage:
    python run_full_coaching.py <transcript.json> <audio.wav> <output_dir>

Example:
    python run_full_coaching.py transcripts/speech.json audio/speech.wav output/coaching_results
"""

import sys
import json
import time
import logging
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
sys.stdout.reconfigure(line_buffering=True)
logger = logging.getLogger("speak-right.coaching")

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules from vocal_analysis
from vocal_analysis.analyze_speech import analyze_speech_for_coaching
from vocal_analysis.generate_ssml import (
    extract_prosody_features,
    format_prosody_for_llm,
    generate_coaching_feedback
)


def run_full_coaching_pipeline(transcript_path: str,
                               audio_path: str,
                               output_dir: str,
                               skip_coaching: bool = False):
    """
    Run the complete speech coaching pipeline.

    Args:
        transcript_path: Path to AWS Transcribe JSON output
        audio_path: Path to audio WAV file
        output_dir: Directory to save all outputs
        skip_coaching: If True, skip AI coaching (useful if no API key)

    Outputs:
        - {output_dir}/analysis/coaching_analysis.json
        - {output_dir}/coaching/coaching_feedback.md
        - {output_dir}/coaching/prosody_data.txt (debug)
    """

    # Setup paths
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    coaching_dir = output_dir / "coaching"
    coaching_dir.mkdir(exist_ok=True)

    # Determine base name for output files
    base_name = Path(audio_path).stem

    # File paths
    coaching_analysis_path = analysis_dir / f"{base_name}_coaching_analysis.json"
    coaching_feedback_path = coaching_dir / f"{base_name}_coaching_feedback.md"
    coaching_insights_path = coaching_dir / f"{base_name}_insights.json"
    prosody_data_path = coaching_dir / f"{base_name}_prosody_data.txt"

    print("=" * 80)
    print("🎙️  SPEECH COACHING PIPELINE")
    print("=" * 80)
    print(f"\nInput files:")
    print(f"  📄 Transcript: {transcript_path}")
    print(f"  🔊 Audio: {audio_path}")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 80)

    # ============================================================================
    # STEP 1: ANALYZE SPEECH
    # ============================================================================
    print("\n" + "=" * 80)
    print("STEP 1/2: ANALYZING SPEECH")
    print("=" * 80)
    print("Extracting acoustic features and speech metrics...\n")

    analyze_speech_for_coaching(transcript_path, audio_path, coaching_analysis_path)

    print(f"\n✅ Analysis complete!")
    print(f"   Saved to: {coaching_analysis_path}")

    # ============================================================================
    # STEP 2: GENERATE AI COACHING FEEDBACK
    # ============================================================================
    print("\n" + "=" * 80)
    print("STEP 2/2: GENERATING AI COACHING FEEDBACK")
    print("=" * 80)

    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if skip_coaching or not api_key:
        print("⚠️  Skipping AI coaching (no ANTHROPIC_API_KEY found)")
        print("\nTo enable AI coaching:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("  python run_full_coaching.py <transcript> <audio> <output_dir>")
        print("\nGenerating prosody data only...")

        # Still generate prosody data for reference
        with open(coaching_analysis_path, 'r') as f:
            coaching_data = json.load(f)

        enriched_words = extract_prosody_features(coaching_data)
        prosody_text = format_prosody_for_llm(enriched_words, coaching_data)

        with open(prosody_data_path, 'w') as f:
            f.write(prosody_text)

        print(f"✅ Prosody data saved to: {prosody_data_path}")

    else:
        print("Analyzing speech patterns with Claude Opus...\n")

        # Load coaching analysis
        with open(coaching_analysis_path, 'r') as f:
            coaching_data = json.load(f)

        # Extract prosody features
        print("📊 Extracting prosody features...")
        enriched_words = extract_prosody_features(coaching_data)

        print("📝 Formatting data for LLM...")
        prosody_text = format_prosody_for_llm(enriched_words, coaching_data)

        # Save prosody data for debugging
        with open(prosody_data_path, 'w') as f:
            f.write(prosody_text)
        print(f"  ✓ Prosody data saved to: {prosody_data_path}")

        # Generate coaching feedback
        transcript = coaching_data['transcript']

        print("🤖 Generating coaching feedback with Claude Opus...")
        print("   (This may take 30-60 seconds for detailed analysis)")

        result = generate_coaching_feedback(transcript, prosody_text, api_key)

        # Save coaching feedback (markdown)
        with open(coaching_feedback_path, 'w') as f:
            f.write(result["coaching_feedback"])

        # Save insights (JSON)
        with open(coaching_insights_path, 'w') as f:
            json.dump(result["insights"], f, indent=2)

        print(f"\n✅ Coaching feedback complete!")
        print(f"   Saved to: {coaching_feedback_path}")
        print(f"   Insights: {coaching_insights_path}")

    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("🎉 PIPELINE COMPLETE!")
    print("=" * 80)

    # Load analysis for summary
    with open(coaching_analysis_path, 'r') as f:
        coaching_data = json.load(f)

    speech_metrics = coaching_data['speech_metrics']
    acoustic_features = coaching_data['acoustic_features']

    print("\n📊 Speech Summary:")
    print(f"   • Total words: {speech_metrics['total_words']}")
    print(f"   • Speaking rate: {speech_metrics['speaking_rate_wpm']:.1f} WPM")
    print(f"   • Filler words: {speech_metrics['filler_word_count']} ({speech_metrics['filler_word_ratio']*100:.1f}%)")
    print(f"   • Long pauses: {speech_metrics['pause_count']}")
    print(f"   • Pitch range: {acoustic_features['parselmouth']['pitch_range_hz']:.1f} Hz")
    print(f"   • Volume variation: {acoustic_features['parselmouth']['intensity_range_db']:.1f} dB")

    print("\n📁 Output Files:")
    print(f"   Analysis:       {coaching_analysis_path}")
    if not skip_coaching and api_key:
        print(f"   AI Coaching:    {coaching_feedback_path}")
        print(f"   AI Insights:    {coaching_insights_path}")
    print(f"   Prosody Data:   {prosody_data_path}")

    print("\n" + "=" * 80)

    return {
        "analysis": str(coaching_analysis_path),
        "coaching_feedback": str(coaching_feedback_path) if (not skip_coaching and api_key) else None,
        "coaching_insights": str(coaching_insights_path) if (not skip_coaching and api_key) else None,
        "prosody_data": str(prosody_data_path)
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_full_coaching.py <transcript.json> <audio.wav> <output_dir> [--skip-coaching]")
        print("\nDescription:")
        print("  Runs the complete speech coaching pipeline:")
        print("    1. Analyze speech (acoustic features + metrics)")
        print("    2. Generate AI coaching feedback (with Claude)")
        print("\nArguments:")
        print("  transcript.json  - AWS Transcribe JSON output with word timestamps")
        print("  audio.wav        - Audio file (WAV format)")
        print("  output_dir       - Directory to save all results")
        print("\nOptions:")
        print("  --skip-coaching  - Skip AI coaching generation")
        print("\nEnvironment:")
        print("  ANTHROPIC_API_KEY - Required for AI coaching (step 2)")
        print("\nExamples:")
        print("  # Full pipeline with AI coaching:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("  python run_full_coaching.py input.json audio.wav output/")
        print("\n  # Without AI coaching:")
        print("  python run_full_coaching.py input.json audio.wav output/ --skip-coaching")
        sys.exit(1)

    transcript_path = sys.argv[1]
    audio_path = sys.argv[2]
    output_directory = sys.argv[3]
    skip_coaching = "--skip-coaching" in sys.argv

    # Validate input files exist
    if not Path(transcript_path).exists():
        print(f"❌ Error: Transcript file not found: {transcript_path}")
        sys.exit(1)

    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)

    try:
        results = run_full_coaching_pipeline(
            transcript_path,
            audio_path,
            output_directory,
            skip_coaching
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
