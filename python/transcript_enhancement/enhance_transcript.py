import ast
import os
from openai import OpenAI
from dotenv import load_dotenv
import boto3
import json

# Load environment variables
load_dotenv()

# Get API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=openai_api_key)

s3_client = boto3.client('s3', region_name = 'ap-south-1')

def enhance_with_chatgpt(transcript_segments):
    
    prompt = f"""You are an expert at enhancing business conversations. 
        
I have a sales call transcription ssml that needs improvement. Please enhance it by:
1. Fixing grammar and sentence structure
2. Making it more professional and clear
3. Maintaining the original meaning and conversational flow
4. Keeping the same speaker structure
5. Adding essential ssml taggs like emphasis for enhanced experiance

Original conversation:
{transcript_segments}

Please provide the enhanced version in the EXACT same format, one line per segment. Do not add any additional commentary, just the enhanced conversation."""
    response = client.responses.create(
model="gpt-5-nano",
input=prompt,
store=True,
)
    print(response.output_text);
    enhanced_script = response.output_text
    return ast.literal_eval(enhanced_script)

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
