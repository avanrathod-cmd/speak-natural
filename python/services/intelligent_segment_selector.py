"""
Intelligent segment selection using Claude AI.

Leverages Claude's coaching analysis to select the most pedagogically valuable
segments for practice, rather than using rule-based heuristics.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import anthropic


def format_transcript_with_timing(words: List[Dict]) -> str:
    """
    Format transcript with timestamps for LLM readability.

    Args:
        words: List of word dictionaries with timing info

    Returns:
        Formatted string with timestamps
    """
    output = []
    current_line = []
    current_start = None
    line_duration = 0

    for i, word in enumerate(words):
        word_text = word.get('word', '')
        start_time = word.get('start_time', 0)
        end_time = word.get('end_time', 0)

        if current_start is None:
            current_start = start_time

        current_line.append(word_text)
        line_duration = end_time - current_start

        # Break line every ~10 seconds or at sentence end
        should_break = False
        if line_duration >= 10:
            should_break = True
        elif word_text.endswith(('.', '!', '?')) and line_duration >= 3:
            should_break = True
        elif i == len(words) - 1:
            should_break = True

        if should_break and current_line:
            line_text = ' '.join(current_line)
            output.append(f"[{current_start:.1f}s - {end_time:.1f}s] {line_text}")
            current_line = []
            current_start = None
            line_duration = 0

    return '\n'.join(output)


def create_segment_selection_prompt(
    transcript_with_timing: str,
    coaching_feedback: str,
    prosody_summary: str,
    max_segments: int = 6
) -> str:
    """
    Create the prompt for Claude to select segments.

    Args:
        transcript_with_timing: Formatted transcript with time ranges
        coaching_feedback: Previously generated coaching feedback
        prosody_summary: Summary of prosody data (optional, can be abbreviated)
        max_segments: Maximum number of segments to select

    Returns:
        Prompt string
    """
    return f"""You are an expert speech coach helping a non-native English speaker improve
their American English delivery.

You have already analyzed their speech and provided detailed coaching feedback.
Now, select {max_segments} specific segments from the transcript that would be MOST VALUABLE for
the speaker to practice.

# SELECTION CRITERIA
Choose segments that:
1. **Demonstrate key issues** - Show clear examples of problems you identified 
(filler words, monotone, wrong emphasis, pace issues)
2. **Have high learning value** - Where fixing the issue creates noticeable improvement
3. **Are self-contained** - 10-20 seconds, complete thoughts
4. **Show variety** - Cover different types of issues (not all the same problem)
5. **Include 1 positive example** - One segment they did well (if any exist)

# ORIGINAL TRANSCRIPT WITH TIMING
{transcript_with_timing}

# YOUR PREVIOUS COACHING ANALYSIS
{coaching_feedback}

# PROSODY OVERVIEW
{prosody_summary}

# YOUR TASK
Select {max_segments} segments and for EACH provide:

1. **Time Range**: Exact start and end times from the transcript above
2. **Selection Reason**: Why this segment is valuable for learning (1-2 sentences)
3. **Original SSML**: SSML markup showing how the user ACTUALLY spoke - preserve fillers, mark words they stressed, show their actual pace
4. **Improved SSML**: SSML markup showing how it SHOULD be spoken - remove fillers, mark words that need emphasis, show proper pace
5. **Primary Issues**: List of specific problems (e.g., ["filler-words", "monotone", "too-fast"])
6. **Coaching Tip**: Specific, actionable advice for this segment (2-3 sentences)
7. **Priority**: "high", "medium", or "low"

# SSML GUIDELINES
Use these tags in BOTH original and improved SSML:
- `<prosody rate="X%">` for pace (85%-115%, use 100% as baseline)
- `<emphasis level="moderate|strong">` for stressed words (mark what user DID stress in original, what SHOULD be stressed in improved)
- `<break time="Xms"/>` for pauses (300-700ms)
- Preserve filler words in original_ssml (um, uh, like, you know, etc.)
- Add proper punctuation in both versions

# OUTPUT FORMAT
Respond with ONLY valid JSON (no markdown code blocks, no explanation):

{{
  "segments": [
    {{
      "segment_id": 1,
      "time_range": {{
        "start": 12.5,
        "end": 18.3
      }},
      "selection_reason": "Demonstrates excessive filler words and weak emphasis on key terms.",
      "original_ssml": "<prosody rate='110%'>So um I <emphasis level='moderate'>think</emphasis> that we should like consider this option.</prosody>",
      "improved_ssml": "<prosody rate='95%'>I <emphasis level='moderate'>think</emphasis> we should <emphasis level='strong'>consider</emphasis> this option.</prosody>",
      "primary_issues": ["filler-words", "weak-emphasis"],
      "coaching_tip": "Remove filler words ('so', 'um', 'like') and add natural emphasis on action words like 'think' and 'consider'.",
      "priority": "high"
    }}
  ],
  "selection_summary": "Brief explanation of why these segments were chosen"
}}"""


def select_segments_with_claude(
    coaching_analysis: Dict[str, Any],
    coaching_feedback: str,
    max_segments: int = 6,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use Claude to intelligently select segments based on coaching analysis.

    Args:
        coaching_analysis: Full coaching analysis JSON (contains words, prosody, etc.)
        coaching_feedback: Previously generated coaching feedback text
        max_segments: Maximum number of segments to select
        api_key: Anthropic API key (uses env var if not provided)

    Returns:
        Dictionary with selected segments and metadata

    Example response:
    {
        "segments": [
            {
                "segment_id": 1,
                "time_range": {"start": 12.5, "end": 18.3},
                "selection_reason": "...",
                "original_ssml": "<prosody rate='110%'>So um I <emphasis>think</emphasis>...</prosody>",
                "improved_ssml": "<prosody rate='95%'>I <emphasis>think</emphasis>...</prosody>",
                "primary_issues": ["filler-words", "monotone"],
                "coaching_tip": "...",
                "priority": "high"
            }
        ],
        "selection_summary": "..."
    }
    """
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    # Extract words from analysis
    words = coaching_analysis.get('words', [])
    if not words:
        words = coaching_analysis.get('word_level_analysis', [])

    if not words:
        raise ValueError("No word-level data found in coaching analysis")

    # Format transcript with timing
    transcript_with_timing = format_transcript_with_timing(words)

    # Create abbreviated prosody summary (don't send full word-by-word to reduce tokens)
    speech_rate = coaching_analysis.get('speech_metrics', {}).get('speaking_rate_wpm', 150)
    prosody_summary = f"Speaking rate: {speech_rate:.1f} WPM\n"
    prosody_summary += "See coaching feedback for detailed prosody issues."

    # Create prompt
    prompt = create_segment_selection_prompt(
        transcript_with_timing=transcript_with_timing,
        coaching_feedback=coaching_feedback,
        prosody_summary=prosody_summary,
        max_segments=max_segments
    )

    # Call Claude
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",  # Use Sonnet for cost efficiency
        max_tokens=8000,
        temperature=0.3,  # Lower temperature for more consistent JSON
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if response_text.strip().startswith('```'):
            # Extract JSON from markdown code block
            lines = response_text.strip().split('\n')
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                elif in_code_block or (not line.strip().startswith('```')):
                    json_lines.append(line)
            response_text = '\n'.join(json_lines)

        result = json.loads(response_text)
        return result
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response from Claude: {e}")
        print(f"Response: {response_text}")
        raise ValueError(f"Claude did not return valid JSON: {e}")


def enrich_segments_with_metadata(
    segments: List[Dict],
    coaching_analysis: Dict[str, Any]
) -> List[Dict]:
    """
    Enrich segments with additional metadata from coaching analysis.

    Args:
        segments: List of segments from Claude
        coaching_analysis: Full coaching analysis

    Returns:
        Enriched segments with word count, duration, etc.
    """
    for segment in segments:
        time_range = segment['time_range']
        start = time_range['start']
        end = time_range['end']

        # Add duration
        segment['duration'] = round(end - start, 2)

        # Map severity from priority
        priority = segment.get('priority', 'medium')
        if priority == 'high':
            segment['severity'] = 'error'
            segment['severity_score'] = 10.0
        elif priority == 'medium':
            segment['severity'] = 'warning'
            segment['severity_score'] = 5.0
        else:
            segment['severity'] = 'good'
            segment['severity_score'] = 0.0

        # Add quality score (inverse of severity for good segments)
        if segment['severity'] == 'good':
            segment['quality_score'] = 10.0
            segment['is_exemplary'] = True
        else:
            segment['quality_score'] = max(0, 10 - segment['severity_score'])
            segment['is_exemplary'] = False

        # Format issues for API response
        issues_list = []
        for issue_type in segment.get('primary_issues', []):
            issues_list.append({
                'type': issue_type,
                'description': segment.get('selection_reason', ''),
                'tip': segment.get('coaching_tip', '')
            })
        segment['issues'] = issues_list

        # Set primary_issue
        segment['primary_issue'] = issues_list[0] if issues_list else None

    return segments


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python intelligent_segment_selector.py <coaching_analysis.json> <coaching_feedback.txt> [max_segments]")
        print("\nThis script uses Claude to select the most valuable segments for practice.")
        print("Requires ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    analysis_path = sys.argv[1]
    feedback_path = sys.argv[2]
    max_segments = int(sys.argv[3]) if len(sys.argv) > 3 else 6

    # Load inputs
    with open(analysis_path, 'r') as f:
        analysis = json.load(f)

    with open(feedback_path, 'r') as f:
        feedback = f.read()

    print(f"🤖 Asking Claude to select {max_segments} most valuable segments...\n")

    # Select segments
    result = select_segments_with_claude(
        coaching_analysis=analysis,
        coaching_feedback=feedback,
        max_segments=max_segments
    )

    # Enrich with metadata
    enriched = enrich_segments_with_metadata(result['segments'], analysis)

    print("=" * 80)
    print(f"SELECTED {len(enriched)} SEGMENTS")
    print("=" * 80)
    print(f"\n{result.get('selection_summary', '')}\n")

    for seg in enriched:
        print(f"\n📍 Segment {seg['segment_id']} [{seg['time_range']['start']:.1f}s - {seg['time_range']['end']:.1f}s]")
        print(f"   Priority: {seg['priority']} | Issues: {', '.join(seg['primary_issues'])}")
        print(f"   Original: \"{seg['original_text']}\"")
        print(f"   Improved: \"{seg['improved_text']}\"")
        print(f"   💡 {seg['coaching_tip']}")

    # Save output
    output_path = Path(analysis_path).parent / "intelligent_segments.json"
    with open(output_path, 'w') as f:
        json.dump({"segments": enriched, **result}, f, indent=2)

    print(f"\n✅ Segments saved to: {output_path}")
