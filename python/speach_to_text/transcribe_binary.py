"""Call the transcribe function from the `transcribe` module.

This script invokes `transcribe_file` with a job name of `my_job` and the
S3 URI `s3://speach-analyzer/Conv with Avisha.webm`.
"""

from transcribe import read_transcription


def main():
    job_name = "my_job"
    file_uri = "s3://speach-analyzer/Conv with Avisha.webm"

    transcription_data = read_transcription(job_name, file_uri)
    if transcription_data:
        print(f"Transcript : {transcription_data}")
    else:
        print("Transcription job failed or did not complete.")


if __name__ == "__main__":
    main()
    
    


    