import sys
import os
from pathlib import Path
import ast
from openai import OpenAI
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent))

from openapi_utils import query_chatgpt_and_show_output

def score_conversation(ssml_transcript):
    prompt = f"""You are an expert conversation analyst.
    I have a sales call transcription ssml that needs review. Please rate it by:
1. Cadence
2. Grammar
3. Vocubuary

Conversation:
{ssml_transcript}

Rate the call on the above criteria out of 100. the output should be in the form of 
<rubric>:<score> in seperate line. Also give overall rating of the conversation 
out of 100 giving 50% weight to first rubrik and 25% to others. 
Also note the you onlyhave to rate the salesperson and not the client.
Dont add any other commentry. 
"""
    response = query_chatgpt_and_show_output(prompt)
    score_dict = {line.split(':')[0]: int(line.split(':')[1])
                for line in response.splitlines()}
    
    print("Conversation Scoring Response:\n", score_dict)
    
    return score_dict
    