from dotenv import load_dotenv
from openai import OpenAI
import os



# Load environment variables
load_dotenv()

# Get API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openapi_client = OpenAI(api_key=openai_api_key)

def query_chatgpt_and_show_output(prompt: str) -> str:
    """
    Query ChatGPT with the given prompt and return the output text.
    
    Args:
        prompt: The prompt string to send to ChatGPT.
        
    Returns:
        str: The output text from ChatGPT.
    """
    response = openapi_client.responses.create(
        model="gpt-5-nano",
        input=prompt,
        store=True,
    )
    return response.output_text