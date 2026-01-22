import sys
from pathlib import Path
import ast

# Add parent directory to path if transcribe is located there
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent))

from enhance_transcript import enhance_with_chatgpt
from aws_utils import write_to_s3, read_json_from_s3

def main():
    job_name = "my_job"
    file_uri = "s3://speach-analyzer/Conv with Avisha.webm"

    transcript_segments = read_json_from_s3(bucket_name="speach-analyzer",
                                        object_key=f"transcriptions/{job_name}" +
                                        "/transcription.json")

    print(f"Original Transcript Segments: {transcript_segments}")
    
    enhanced_script = enhance_with_chatgpt(transcript_segments)
    print(f"\n\n Enhanced Script:\n {enhanced_script}\n\n")
    
    write_to_s3(bucket_name="speach-analyzer",
                object_key=f"transcriptions/{job_name}/enhanced_transcription.json",
                content=str(enhanced_script))
    

if __name__ == "__main__":
    main()
    