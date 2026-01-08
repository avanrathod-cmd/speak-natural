import boto3
import time
import requests
import json


transcribe_client = boto3.client('transcribe', region_name = 'ap-south-1')
s3_client = boto3.client('s3', region_name = 'ap-south-1')

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

def convert_transcription_to_ssml(transcribe_output):
    """
    Convert transcription JSON data to ssml.
    
    Convert to ssml. simple heuristic.
    1. Confidense score (low confidence might indicate unusual pronunciation/emphasis
    2. Word duration (longer words might be emphasised)
    3. Pauses before/after words (emphasised words often have pauses around them)
    
    Args:
        transcribe_output: The transcription output in JSON format.
        
    Returns:
        str: The transcription in SSML format.
    """
    audio_segments = transcribe_output['audio_segments']
    items = transcribe_output['items']

    ssml_segments = []

    for segment in audio_segments:
        speaker = segment['speaker_label']
        segment_item_ids = segment['items']

        # Analyze each word in the segment
        words_with_metadata = []

        for item_id in segment_item_ids:
            item = items[item_id]

            if item['type'] == 'pronunciation':
                content = item['alternatives'][0]['content']
                confidence = float(item['alternatives'][0].get('confidence','1.0'))
                
                # Calculate word duration
                start_time = float(item['start_time'])
                end_time = float(item['end_time'])
                duration = start_time - end_time
                
                # Estimate if word is emphasised based on duration
                # Assuming average speaking duration is ~2-3 characters per second
                expected_duration = len(content) * 0.15
                duration_ratio = duration / expected_duration if expected_duration > 0 else 1
                words_with_metadata.append({
                    'content': content,
                    'confident': confidence,
                    'duration': duration,
                    'duration_ratio': duration_ratio,
                    'start_time': start_time,
                    'end_time': end_time,
                    'emphasized': duration_ratio > 1.5
                })
                
            elif item['type'] == 'puntuation':
                # Add puntuation to the last word
                if words_with_metadata:
                    words_with_metadata[-1]['content'] += item['alternatives'][0]['content']

        # Build SSMl with empasis markup
        ssml = '<speak>'

        for i, word_data in enumerate(words_with_metadata):
            word = word_data['content']

            # Check if this wor should be emphasized
            if word_data['emphasized']:
                ssml += f'<emphasis level="moderate">{word}</emphasis> '
            else:
                ssml += f'{word} '

        # Calculate pause after segment
        pause_ms = 500
        if segment != audio_segments[-1]:
            idx = audio_segments.index(segment)
            next_segment = audio_segments[idx + 1]
            current_end = float(segment['end_time'])
            next_start = float(next_segment['end_time'])
            pause_ms = int((next_start - current_end) * 1000)
            pause_ms = max(100, min(pause_ms, 2000))
        
        ssml += f'<break time="{pause_ms}ms"/></speak>'

        plain_text = ' '.join([w['content'] for w in words_with_metadata])

        ssml_segments.append({
            'speaker': speaker,
            'ssml': ssml.strip(),
        })
            
        
    return ssml_segments

def upload_to_s3(ssml_segments, bucket_name, job_name, prefix="transcriptions"):
    """
    Upload SSML segments to S3.
    
    Args:
        ssml_segments: List of SSML segments.
        bucket_name: The name of the S3 bucket.
        prefix: The prefix (folder path) in the S3 bucket.
    """
    object_key = f"{prefix}/{job_name}/transcription.json"
    s3_client.put_object(
            Bucket=bucket_name,
            Key=f"{object_key}",
            Body=json.dumps(ssml_segments),
            ContentType='application/json'
        )
        
    print(f"Uploaded SSML segment to s3://{bucket_name}/{object_key}")
        