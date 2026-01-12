from pydub import AudioSegment
from elevenlabs import ElevenLabs, VoiceSettings
import os
from dotenv import load_dotenv
import tempfile
import io
from io import BytesIO
import boto3

s3_client = boto3.client("s3",region_name = 'ap-south-1')
load_dotenv()
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

pause_ms = 500

def get_audio_from_s3(bucket_name = "speach-analyzer",
                    object_key = "Conv with Avisha.webm"):
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    audio_data = response['Body'].read()
    return AudioSegment.from_file(BytesIO(audio_data), format=object_key.split(".")[-1])

def get_speaker_clips(transcript_segments, audio):
    speaker_clips = {}
    
    for segment in transcript_segments:
        speaker = segment['speaker_label']
        start_ms = float(segment['start_time']) * 1000
        end_ms = float(segment['end_time']) * 1000
            
        # Extract this segment
        clip = audio[start_ms:end_ms]
        
        if speaker not in speaker_clips:
            speaker_clips[speaker] = []
            
        speaker_clips[speaker].append(clip)
    return speaker_clips

def combine_individual_speaker_clips(speaker_clips, dir = None):
    # Combine clips for each speaker until we have enough audio
    output_dir = dir if dir else tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)

    voice_samples = {}
    
    for speaker, clips in speaker_clips.items():
        combined = AudioSegment.empty()
            
        # Combine clips until we reach min_duration
        for clip in clips:
            combined += clip
            # if len(combined) >= min_duration:
            #     break
            
            # Save the voice sample
            sample_path = os.path.join(output_dir, f"{speaker}_voice_sample.mp3")
            combined.export(sample_path, format="mp3")
            voice_samples[speaker] = sample_path
            
            print(f"Extracted {len(combined)/1000:.2f}s of audio for {speaker}")
    
    return voice_samples

def get_voice_mapping_with_elevenlabs(voice_samples):
    voice_mapping = {}
    for speaker, sample_path in voice_samples.items():
        print(f"Cloning voice for {speaker}...path {sample_path}")
        
        #Clone voice using ElevenLabs API
        voice = elevenlabs_client.voices.ivc.create(
        name=f"Cloned_{speaker}",
        files=[BytesIO(open(sample_path,"rb").read())]
        )
        
        voice_mapping[speaker] = voice.voice_id
        print(f"Cloned voice for {speaker} with voice ID: {voice.voice_id}")
    return voice_mapping

def generate_speech_for_segments(segments, voice_mapping, dir=None):
    dir = dir if dir else tempfile.gettempdir()
    audio_files = []

    for i, segment in enumerate(segments):
        speaker = segment['speaker']
        text = segment['ssml']
        voice_id = voice_mapping.get(speaker)
        
        if not voice_id:
            print(f"Warning: No voice for {speaker}, skipping...")
            continue
        
        print(f"Generating speech for {speaker}: {text[:50]}...")
        
        audio_generator = generate_voice_with_elevenlabs(text, voice_id)
        
        filename = os.path.join(dir, f"generated_{speaker}_{i}.mp3")
        with open(filename, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
        
        audio_files.append(filename)
        print(f"Saved: {filename}")
    
    # Combine all generated audio files into one
    output_file  = "final-combined.mp3"


    out = os.path.join(dir, output_file)
    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=pause_ms)

    for audio_file in audio_files:
        segment = AudioSegment.from_file(audio_file)
        combined += segment + pause

    combined.export(out, format="mp3")
    print(f"\nFinal audio saved to: {output_file}")
    print(f"Total duration: {len(combined)/1000:.2f} seconds")
    return out, combined

def generate_voice_with_elevenlabs(text, voice_id):
    return elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.0,
                use_speaker_boost=True
            )
        )