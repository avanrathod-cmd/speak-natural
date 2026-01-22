import sys
from pathlib import Path
from conversation_scorer import score_conversation
from aws_utils import get_audio_segment_from_s3

sys.path.insert(0, str(Path(__file__).parent.parent / "speach_to_text"))
sys.path.insert(0, str(Path(__file__).parent))

from transcribe import read_transcription, convert_transcription_to_ssml

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

def process_transcript(name, object_key, bucket_name="speech-analyzer"):
    
    file_uri = f"s3://{bucket_name}/{object_key}"
    transcription_data = read_transcription(job_name=name, file_uri=file_uri)
    transcrition_ssml = convert_transcription_to_ssml(
        transcription_data['results'])
    
    score_conversation(transcrition_ssml)
    
    
def main():
    bucket_name = "speach-analyzer"
    audios = {
        "raw_audio": "Conv with Avisha.webm",
        "enhanced_audio": "enhanced_audios/enhanced_Conv with Avisha.mp3"
    }
    
    for name, object_key in audios.items():
        process_transcript(name=name, object_key=object_key, bucket_name=bucket_name)



if __name__ == "__main__":
    main()