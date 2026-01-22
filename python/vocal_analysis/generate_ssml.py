"""
SSML generation from speech prosody analysis.
Uses vocal analysis data to generate SSML markup that reproduces speech patterns.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import anthropic
import os


def extract_prosody_features(coaching_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract word-level prosody features from coaching data.

    Returns a list of enriched word data with:
    - word: text
    - start_time, end_time, duration
    - pitch_hz and pitch_relative (% deviation from mean)
    - intensity_db and intensity_relative (% deviation from mean)
    - pause_after (if significant pause follows)
    """
    word_level = coaching_data.get('word_level_analysis', [])

    # Get baseline values
    pitch_mean = coaching_data['acoustic_features']['parselmouth']['pitch_mean_hz']
    pitch_std = coaching_data['acoustic_features']['parselmouth']['pitch_std_hz']
    intensity_mean = coaching_data['acoustic_features']['parselmouth']['intensity_mean_db']
    intensity_std = coaching_data['acoustic_features']['parselmouth']['intensity_std_db']

    enriched_words = []

    for i, word_data in enumerate(word_level):
        word_info = {
            'word': word_data['word'],
            'start_time': word_data['start_time'],
            'end_time': word_data['end_time'],
            'duration': word_data['end_time'] - word_data['start_time'],
        }

        # Calculate relative pitch (as percentage deviation from mean)
        if word_data['pitch_hz'] is not None:
            pitch_deviation = (word_data['pitch_hz'] - pitch_mean) / pitch_mean * 100
            word_info['pitch_hz'] = word_data['pitch_hz']
            word_info['pitch_relative'] = round(pitch_deviation, 1)
            # Also categorize: low, medium, high
            if word_data['pitch_hz'] < pitch_mean - pitch_std:
                word_info['pitch_category'] = 'low'
            elif word_data['pitch_hz'] > pitch_mean + pitch_std:
                word_info['pitch_category'] = 'high'
            else:
                word_info['pitch_category'] = 'medium'
        else:
            word_info['pitch_hz'] = None
            word_info['pitch_relative'] = None
            word_info['pitch_category'] = 'medium'

        # Calculate relative intensity (as percentage deviation from mean)
        intensity_deviation = (word_data['intensity_db'] - intensity_mean) / abs(intensity_mean) * 100
        word_info['intensity_db'] = word_data['intensity_db']
        word_info['intensity_relative'] = round(intensity_deviation, 1)
        # Categorize: soft, medium, loud
        if word_data['intensity_db'] < intensity_mean - intensity_std:
            word_info['intensity_category'] = 'soft'
        elif word_data['intensity_db'] > intensity_mean + intensity_std:
            word_info['intensity_category'] = 'loud'
        else:
            word_info['intensity_category'] = 'medium'

        # Check for pause after this word
        if i < len(word_level) - 1:
            next_word = word_level[i + 1]
            pause_duration = next_word['start_time'] - word_data['end_time']
            if pause_duration > 0.3:  # Significant pause (300ms+)
                word_info['pause_after'] = round(pause_duration * 1000)  # Convert to ms

        enriched_words.append(word_info)

    return enriched_words


def format_prosody_for_llm(enriched_words: List[Dict[str, Any]],
                           coaching_data: Dict[str, Any]) -> str:
    """
    Format prosody data into a clear text representation for LLM prompt.
    """
    # Get overall speech metrics
    speech_rate = coaching_data['speech_metrics']['speaking_rate_wpm']

    # Categorize speech rate
    if speech_rate < 130:
        rate_category = "slow"
    elif speech_rate > 170:
        rate_category = "fast"
    else:
        rate_category = "medium"

    output = f"Speech Rate: {speech_rate:.1f} WPM ({rate_category})\n\n"
    output += "Word-by-word prosody data:\n"
    output += "=" * 80 + "\n\n"

    for word_info in enriched_words:
        output += f"Word: '{word_info['word']}'\n"
        output += f"  Duration: {word_info['duration']:.3f}s\n"

        if word_info['pitch_relative'] is not None:
            output += f"  Pitch: {word_info['pitch_hz']:.1f} Hz ({word_info['pitch_relative']:+.1f}% from mean) [{word_info['pitch_category']}]\n"
        else:
            output += f"  Pitch: [unvoiced/unclear]\n"

        output += f"  Intensity: {word_info['intensity_db']:.1f} dB ({word_info['intensity_relative']:+.1f}% from mean) [{word_info['intensity_category']}]\n"

        if 'pause_after' in word_info:
            output += f"  >>> PAUSE AFTER: {word_info['pause_after']}ms\n"

        output += "\n"

    return output


def create_ssml_prompt(transcript: str, prosody_data: str) -> str:
    """
    Create the prompt for Claude to generate SSML.
    """
    prompt = f"""You are an expert in SSML (Speech Synthesis Markup Language) generation. Given the transcript and detailed prosody analysis below, generate SSML markup that would reproduce the same speech patterns.

TRANSCRIPT:
{transcript}

PROSODY ANALYSIS:
{prosody_data}

Your task is to generate SSML markup using the following tags appropriately:
- <prosody pitch="..."> for pitch variations (use values like "-20%", "+10%", "low", "medium", "high")
- <prosody volume="..."> for intensity/volume (use values like "soft", "medium", "loud", "-6dB", "+3dB")
- <prosody rate="..."> for speech rate changes (use "slow", "medium", "fast", or percentage like "85%")
- <emphasis level="..."> for emphasized words (combine high pitch + loud volume)
- <break time="...ms"/> for pauses between words

Guidelines:
1. Use relative pitch values (percentages) based on the pitch_relative column
2. Use volume categories based on intensity_category
3. Only add prosody tags when there's a significant deviation (>15% for pitch, or categorized as high/low)
4. Use <emphasis> for words that have both high pitch AND loud volume
5. Add <break> tags for pauses >= 300ms
6. Group consecutive words with similar prosody into single <prosody> tags when possible
7. Keep the output clean and readable

Generate ONLY the SSML markup, without any explanation or additional text."""

    return prompt


def create_coaching_prompt(transcript: str, prosody_data: str) -> str:
    """
    Create a prompt for speech coaching analysis and improvement suggestions.
    """
    prompt = f"""You are an expert speech coach specializing in helping non-native speakers improve their American English speech patterns.

Analyze the speech below and provide detailed coaching feedback.

TRANSCRIPT:
{transcript}

DETAILED PROSODY ANALYSIS:
{prosody_data}

Your task is to provide a comprehensive coaching report with three sections:

# SECTION 1: SPEECH CRITIQUE
Analyze the current speech patterns against natural USA English standards:
- **Overall Assessment**: Evaluate pitch variation, volume dynamics, speaking rate, and pause placement
- **Specific Issues**: Identify unnatural patterns such as:
  - Monotone sections or erratic pitch jumps
  - Inappropriate emphasis (stressing function words instead of content words)
  - Missing or awkward pauses
  - Too fast/slow speech rate for the context
  - Volume inconsistencies
- **Comparison to USA English Norms**: How does this deviate from natural American speech?
  - Natural pitch range: ~50-100 Hz variation for conversational speech
  - Speaking rate: 140-160 WPM conversational, 160-180 moderate-fast
  - Emphasis: Content words (nouns, verbs, adjectives) should have more stress than function words (articles, prepositions)
  - Pauses: Natural at clause boundaries, after key points, not mid-phrase

Rate the speech on a scale of 1-10 for naturalness, where 10 is native-level USA English.

# SECTION 2: IMPROVED SSML
Generate SSML markup that represents an IMPROVED version of this speech - NOT an exact reproduction, but how it SHOULD sound for natural USA English delivery. Focus on:
- More natural pitch contours (smooth transitions, appropriate rises/falls)
- Better emphasis patterns (stress content words appropriately)
- Natural pause placement (at clause boundaries, for emphasis)
- Appropriate speaking rate adjustments
- Natural volume dynamics

Use these SSML tags:
- <prosody pitch="..."> - use "+5%", "-10%", "medium", "high", "low"
- <prosody volume="..."> - use "soft", "medium", "loud", "x-loud"
- <prosody rate="..."> - use "slow", "medium", "fast", or "95%", "105%"
- <emphasis level="moderate|strong"> - for natural emphasis on key words
- <break time="...ms"/> - for natural pauses (300-500ms for short pauses, 700-1000ms for longer breaks)

# SECTION 3: COACHING GUIDANCE
Provide specific, actionable advice on what the speaker should practice:
- **Priority Issues**: What are the top 3 things to focus on first?
- **Specific Word Examples**: Point out 5-10 specific words from the transcript where emphasis/pitch should change, with before/after guidance
- **Practice Exercises**: What should they practice to develop these skills?
- **Progress Markers**: How will they know they're improving?

Format your response clearly with headers and bullet points for readability."""

    return prompt


def generate_ssml_with_claude(transcript: str,
                              prosody_data: str,
                              api_key: Optional[str] = None) -> str:
    """
    Call Claude API to generate SSML from prosody data.
    """
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = create_ssml_prompt(transcript, prosody_data)

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=8000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def generate_coaching_feedback(transcript: str,
                               prosody_data: str,
                               api_key: Optional[str] = None) -> str:
    """
    Call Claude API to generate comprehensive speech coaching feedback.

    Returns a detailed analysis including:
    - Critique of current speech patterns
    - Improved SSML markup
    - Actionable coaching guidance
    """
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = create_coaching_prompt(transcript, prosody_data)

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=16000,  # Increased for detailed coaching feedback
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def generate_ssml_from_coaching_data(coaching_json_path: str,
                                     output_path: Optional[str] = None,
                                     api_key: Optional[str] = None) -> str:
    """
    Main function: Generate SSML from coaching analysis JSON.

    Args:
        coaching_json_path: Path to coaching analysis JSON file
        output_path: Optional path to save SSML output
        api_key: Optional Anthropic API key (otherwise uses env var)

    Returns:
        Generated SSML string
    """
    # Load coaching data
    with open(coaching_json_path, 'r') as f:
        coaching_data = json.load(f)

    print("📊 Extracting prosody features...")
    enriched_words = extract_prosody_features(coaching_data)

    print("📝 Formatting data for LLM...")
    prosody_text = format_prosody_for_llm(enriched_words, coaching_data)

    # Optionally save the formatted prosody data for inspection
    if output_path:
        prosody_debug_path = Path(output_path).parent / f"{Path(output_path).stem}_prosody_data.txt"
        with open(prosody_debug_path, 'w') as f:
            f.write(prosody_text)
        print(f"  ✓ Prosody data saved to: {prosody_debug_path}")

    transcript = coaching_data['transcript']

    print("🤖 Generating SSML with Claude...")
    ssml = generate_ssml_with_claude(transcript, prosody_text, api_key)

    # Save SSML if output path provided
    if output_path:
        with open(output_path, 'w') as f:
            f.write(ssml)
        print(f"  ✓ SSML saved to: {output_path}")

    return ssml


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_ssml.py <coaching_analysis.json> [output_file] [options]")
        print("\nOptions:")
        print("  --test-mode: Extract prosody data only, don't call Claude API")
        print("  --coaching: Generate comprehensive coaching feedback (default)")
        print("  --ssml-only: Generate SSML reproduction only")
        print("\nEnvironment:")
        print("  Set ANTHROPIC_API_KEY environment variable for API access")
        print("\nExamples:")
        print("  python generate_ssml.py input.json --test-mode")
        print("  python generate_ssml.py input.json output.txt --coaching")
        print("  python generate_ssml.py input.json output.ssml --ssml-only")
        sys.exit(1)

    coaching_json = sys.argv[1]
    test_mode = "--test-mode" in sys.argv
    coaching_mode = "--coaching" in sys.argv or (not "--ssml-only" in sys.argv and not test_mode)
    ssml_only_mode = "--ssml-only" in sys.argv

    output_file = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--"):
            output_file = arg
            break

    # If no output specified, create one based on input filename and mode
    if output_file is None:
        if coaching_mode:
            output_file = Path(coaching_json).parent / f"{Path(coaching_json).stem}_coaching_feedback.md"
        else:
            output_file = Path(coaching_json).parent / f"{Path(coaching_json).stem}_generated.ssml"

    if test_mode:
        print("🧪 TEST MODE: Extracting prosody data only (no API call)\n")

        # Load and extract data
        with open(coaching_json, 'r') as f:
            coaching_data = json.load(f)

        print("📊 Extracting prosody features...")
        enriched_words = extract_prosody_features(coaching_data)

        print("📝 Formatting data for LLM...")
        prosody_text = format_prosody_for_llm(enriched_words, coaching_data)

        # Save prosody data
        prosody_debug_path = Path(output_file).parent / f"{Path(output_file).stem}_prosody_data.txt"
        with open(prosody_debug_path, 'w') as f:
            f.write(prosody_text)
        print(f"  ✓ Prosody data saved to: {prosody_debug_path}")

        # Show sample of what would be sent to LLM
        print("\n" + "=" * 80)
        print("Sample of prosody data (first 20 words):")
        print("=" * 80)
        lines = prosody_text.split('\n')
        print('\n'.join(lines[:100]))
        print(f"\n... ({len(enriched_words)} total words)")

        print("\n✅ Test complete! To generate actual output, set ANTHROPIC_API_KEY and run without --test-mode")

    elif coaching_mode:
        print("🎯 COACHING MODE: Generating comprehensive speech feedback\n")

        # Load and extract data
        with open(coaching_json, 'r') as f:
            coaching_data = json.load(f)

        print("📊 Extracting prosody features...")
        enriched_words = extract_prosody_features(coaching_data)

        print("📝 Formatting data for LLM...")
        prosody_text = format_prosody_for_llm(enriched_words, coaching_data)

        transcript = coaching_data['transcript']

        print("🤖 Generating coaching feedback with Claude Opus...")
        coaching_result = generate_coaching_feedback(transcript, prosody_text)

        # Save coaching feedback
        with open(output_file, 'w') as f:
            f.write(coaching_result)
        print(f"  ✓ Coaching feedback saved to: {output_file}")

        print("\n" + "=" * 80)
        print("COACHING FEEDBACK:")
        print("=" * 80)
        print(coaching_result)

    else:  # ssml_only_mode
        print("📝 SSML MODE: Generating SSML reproduction\n")
        ssml_result = generate_ssml_from_coaching_data(coaching_json, output_file)

        print("\n" + "=" * 80)
        print("Generated SSML:")
        print("=" * 80)
        print(ssml_result)
