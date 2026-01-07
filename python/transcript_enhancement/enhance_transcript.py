import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=openai_api_key)


def convert_to_script(transcript_segments):
    """
    Convert transcript segments to script format, combining consecutive 
    segments from the same speaker.
    
    Args:
        transcript_segments: List of transcript segment dictionaries
        
    Returns:
        list: List of tuples (speaker_label, combined_text)
    """
    if not transcript_segments:
        return []
    
    script = []
    current_speaker = transcript_segments[0]['speaker_label']
    current_text = transcript_segments[0]['transcript']
    
    for segment in transcript_segments[1:]:
        speaker = segment['speaker_label']
        text = segment['transcript']
        
        if speaker == current_speaker:
            # Same speaker - combine the text
            current_text += ' ' + text
        else:
            # Different speaker - save current and start new
            script.append((current_speaker, current_text))
            current_speaker = speaker
            current_text = text
    
    # Don't forget the last speaker's text
    script.append((current_speaker, current_text))
    
    return script

def enhance_with_chatgpt(conv_transcript):
    
    prompt = f"""You are an expert at enhancing business conversations. 
        
I have a sales call transcription that needs improvement. Please enhance it by:
1. Fixing grammar and sentence structure
2. Making it more professional and clear
3. Maintaining the original meaning and conversational flow
4. Keeping the same speaker structure

Original conversation:
{conv_transcript}

Please provide the enhanced version in the EXACT same format (speaker: text), one line per segment. Do not add any additional commentary, just the enhanced conversation."""
    response = client.responses.create(
  model="gpt-5-nano",
  input=prompt,
  store=True,
)
    print(response.output_text);
    enhanced_script = response.output_text
    return enhanced_script

def parse_enhanced_script_to_segments(enhanced_script):
    """
    Parse the enhanced script back into structured format.
    
    Args:
        enhanced_script: str, enhanced script text
        
    Returns:
        list: List of dictionaries with 'speaker_label' and 'transcript'
    """
    # parse enhanced script to segments
    segments = []
    lines = enhanced_script.strip().split('\n')

    for line in lines:
        if ':' not in line:
            continue
        
        # Split on first colon only
        parts = line.split(':', 1)
        if len(parts) == 2:
            speaker = parts[0].strip()
            text = parts[1].strip()
            
            if text:  # Only add if there's actual text
                segments.append({
                    'speaker': speaker,
                    'text': text
                })
    return segments
