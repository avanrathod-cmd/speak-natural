"""Call the transcribe function from the `transcribe` module.

This script invokes `transcribe_file` with a job name of `my_job` and the
S3 URI `s3://speach-analyzer/Conv with Avisha.webm`.
"""

import transcribe

def main():
    job_name = "my_job"
    file_uri = "s3://speach-analyzer/Conv with Avisha.webm"

    transcription_data = transcribe.read_transcription(job_name, file_uri)
    transcrition_ssml = transcribe.convert_transcription_to_ssml(transcription_data['results'])
    if transcription_data:
        print(f"Transcript : {transcrition_ssml}")
    else:
        print("Transcription job failed or did not complete.")
        
    
    transcribe.upload_to_s3(ssml_segments=transcrition_ssml,
                            job_name = "my_job", bucket_name="speach-analyzer",
                            prefix="transcriptions")


if __name__ == "__main__":
    main()
    
    


    