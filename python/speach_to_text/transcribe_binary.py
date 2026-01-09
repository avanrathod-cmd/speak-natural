"""Call the transcribe function from the `transcribe` module.

This script invokes `transcribe_file` with a job name of `my_job` and the
S3 URI `s3://speach-analyzer/Conv with Avisha.webm`.
"""
import sys
from pathlib import Path
import transcribe

# Add parent directory to path if transcribe is located there
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent))

from aws_utils import write_to_s3, read_json_from_s3

def main():
    job_name = "my_job"
    file_uri = "s3://speach-analyzer/Conv with Avisha.webm"

    transcription_data = transcribe.read_transcription(job_name, file_uri)
    transcrition_ssml = transcribe.convert_transcription_to_ssml(transcription_data['results'])
    if transcription_data:
        print(f"Transcript : {transcrition_ssml}")
    else:
        print("Transcription job failed or did not complete.")
        
    write_to_s3(bucket_name="speach-analyzer",
                object_key=f"transcriptions/{job_name}/transcription.json",
                content=str(transcrition_ssml))


if __name__ == "__main__":
    main()
    
    


    