import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import from subdirectories
from speach_to_text.transcribe import read_transcription, convert_transcription_to_ssml
from transcript_enhancement.enhance_transcript import enhance_with_chatgpt, parse_enhanced_script_to_segments
import argparse
from text_to_speach.text_to_speach import(
    get_audio_from_s3,
    get_speaker_clips,
    combine_individual_speaker_clips,
    get_voice_mapping_with_elevenlabs,
    generate_speech_for_segments
)

def main():
    parser = argparse.ArgumentParser(description="Process audio files for transcription and enhancement")
    parser.add_argument("--bucket", default="speach-analyzer", help="S3 bucket name")
    parser.add_argument("--key", default="Conv with Avisha.webm", help="S3 object key")
    parser.add_argument("--job-name", default="speak-right-transcription-job", help="Transcription job name")
    
    args = parser.parse_args()
    
    bucket_name = args.bucket
    object_key = args.key
    job_name = args.job_name
    
    process_audio(bucket_name, object_key, transcribe_job_name=job_name)


def process_audio(bucket_name, object_key, transcribe_job_name="speak-right-transcription-job"):
    job_name = transcribe_job_name
    file_uri = f"s3://{bucket_name}/{object_key}"
    
    print("=" * 50)
    print("Step 1: Transcribe audio from S3")
    print("=" * 50)
    transcription_data = read_transcription(job_name, file_uri)
    transcription_ssml = convert_transcription_to_ssml(transcription_data['results'])
    
    print(f"✓ Transcription complete. Found {len(transcription_ssml)} segments")
    
    print("\n" + "=" * 50)
    print("Step 2: Enhance script with ChatGPT")
    print("=" * 50)
    enhanced_script = enhance_with_chatgpt(transcription_ssml)
    print("✓ Script enhanced")
    
    print("\n" + "=" * 50)
    print("Step 3: Get original audio from S3")
    print("=" * 50)
    audio = get_audio_from_s3(bucket_name, object_key)
    print(f"✓ Audio loaded: {len(audio)/1000:.2f} seconds")
    
    print("\n" + "=" * 50)
    print("Step 4: Extract speaker clips from original audio")
    print("=" * 50)
    speaker_clips = get_speaker_clips(transcription_data['results']['audio_segments'], audio)
    print(f"✓ Extracted clips for {len(speaker_clips)} speakers")
    
    print("\n" + "=" * 50)
    print("Step 5: Combine individual speaker clips to voice samples")
    print("=" * 50)
    voice_samples = combine_individual_speaker_clips(speaker_clips)
    print(f"✓ Created voice samples: {voice_samples}")
    
    print("\n" + "=" * 50)
    print("Step 6: Clone voices with ElevenLabs")
    print("=" * 50)
    voice_mapping = get_voice_mapping_with_elevenlabs(voice_samples)
    print(f"✓ Voice mapping created: {voice_mapping}")
    
    print("\n" + "=" * 50)
    print("Step 7: Generate speech for enhanced segments")
    print("=" * 50)
    final_audio_path = generate_speech_for_segments(enhanced_script, voice_mapping)
    print(f"✓ Final audio generated: {final_audio_path}")
    
    print("\n" + "=" * 50)
    print("Processing Complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()