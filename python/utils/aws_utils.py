import boto3
import json


s3_client = boto3.client('s3', region_name = 'ap-south-1')
def read_json_from_s3(bucket_name = "speach-analyzer",
                    object_key = "transcriptions/my_job/transcription.json"):
    """
    Read json content from an S3 object.
    Args:
        bucket_name: The name of the S3 bucket
        object_key: The key (path) of the S3 object
    Returns:
        dict: Parsed JSON content
    """ 
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)
    return json_content

def write_to_s3(bucket_name, object_key, content):
    """
    Write content to an S3 object.
    
    Args:
        bucket_name: The name of the S3 bucket
        object_key: The key (path) of the S3 object
        content: The content to write (string)
    """
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=content)
    print(f"Content written to s3://{bucket_name}/{object_key}")
    
def save_audio_to_s3(audio_segment, bucket_name, object_key, format="mp3"):
    """
    Save an AudioSegment to S3.
    
    Args:
        audio_segment: The AudioSegment object to save
        bucket_name: The S3 bucket name
        object_key: The S3 object key (path)
        format: Audio format (mp3, wav, etc.)
    """
    # Export AudioSegment to bytes
    audio_bytes = BytesIO()
    audio_segment.export(audio_bytes, format=format)
    audio_bytes.seek(0)  # Reset position to beginning
    
    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=audio_bytes.getvalue()
    )
    print(f"Saved audio to s3://{bucket_name}/{object_key}")
    
    