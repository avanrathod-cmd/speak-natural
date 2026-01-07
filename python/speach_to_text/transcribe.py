import boto3
import time
import requests

transcribe_client = boto3.client('transcribe', region_name = 'ap-south-1')
def transcribe_file_from_s3(job_name, file_uri):
    """
    This Python function transcribes a file from an S3 bucket given the job name and file URI.
    
    :param job_name: A string representing the name of the transcription job
    :param file_uri: The `file_uri` parameter is a Uniform Resource Identifier (URI) that specifies the
    location of the file you want to transcribe. In this case, it likely refers to the location of a
    file stored in an Amazon S3 bucket, as indicated by the function name `transcribe_file_from_s
    """
    # Start transcription job
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        MediaFormat='wav',  # or 'mp3', 'mp4', 'flac'
        LanguageCode='en-US',
        Settings = {
            'ShowSpeakerLabels':True,
            'MaxSpeakerLabels': 10}
    )
    
    # Wait for job to complete
    max_tries = 60
    while max_tries > 0:
        max_tries -= 1
        job = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
        
        if job_status in ['COMPLETED', 'FAILED']:
            print(f"Job {job_name} is {job_status}.")
            if job_status == 'COMPLETED':
                transcript_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
                print(f"Download transcript from: {transcript_uri}")
                return transcript_uri
            break
        else:
            print(f"Waiting for {job_name}. Status: {job_status}")
            time.sleep(10)
            

def read_transcription(job_name, file_uri = "s3://speach-analyzer/Conv with Avisha.webm"):
    """
    Fetch and parse AWS Transcribe results from S3
    
    Args:
        job_name: The transcription job name
        file_uri: The S3 URI of the media file
        
    Returns:
        dict: Parsed transcription results
    """
    transcribe_url = transcribe_file_from_s3( job_name, file_uri)
    
    # Fetch the transcription JSON
    response = requests.get(transcribe_url)
    response.raise_for_status()  # Raise an error for bad status codes
    
    # Parse the JSON
    transcription_data = response.json()
    
    return transcription_data