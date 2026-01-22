"""
Voice cloning service using ElevenLabs API.

Handles extracting speaker audio samples from transcripts and cloning voices.
"""

import os
import tempfile
from io import BytesIO
from typing import Dict, List, Optional, Generator
from pathlib import Path

from pydub import AudioSegment
from elevenlabs import ElevenLabs, VoiceSettings
from dotenv import load_dotenv

load_dotenv()


class VoiceCloningService:
    """Service for cloning voices using ElevenLabs API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the voice cloning service.

        Args:
            api_key: ElevenLabs API key. Uses ELEVENLABS_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY must be set")

        self.client = ElevenLabs(api_key=self.api_key)

    def extract_speaker_clips(
        self,
        audio: AudioSegment,
        transcript_segments: List[Dict]
    ) -> Dict[str, List[AudioSegment]]:
        """
        Extract audio clips for each speaker from transcript segments.

        Args:
            audio: Full audio as pydub AudioSegment
            transcript_segments: List of transcript segments with speaker_label, start_time, end_time

        Returns:
            Dictionary mapping speaker labels to lists of audio clips
        """
        speaker_clips = {}

        for segment in transcript_segments:
            speaker = segment.get('speaker_label')
            if not speaker:
                continue

            start_ms = float(segment['start_time']) * 1000
            end_ms = float(segment['end_time']) * 1000

            clip = audio[start_ms:end_ms]

            if speaker not in speaker_clips:
                speaker_clips[speaker] = []

            speaker_clips[speaker].append(clip)

        return speaker_clips

    def combine_speaker_clips(
        self,
        speaker_clips: Dict[str, List[AudioSegment]],
        output_dir: Optional[str] = None,
        min_duration_ms: int = 10000
    ) -> Dict[str, str]:
        """
        Combine clips for each speaker into voice sample files.

        Args:
            speaker_clips: Dictionary mapping speaker labels to audio clips
            output_dir: Directory to save voice samples. Uses temp dir if not provided.
            min_duration_ms: Minimum duration for voice samples (default 10 seconds)

        Returns:
            Dictionary mapping speaker labels to voice sample file paths
        """
        output_dir = output_dir or tempfile.mkdtemp()
        os.makedirs(output_dir, exist_ok=True)

        voice_samples = {}

        for speaker, clips in speaker_clips.items():
            combined = AudioSegment.empty()

            for clip in clips:
                combined += clip
                # Stop once we have enough audio
                if len(combined) >= min_duration_ms:
                    break

            if len(combined) > 0:
                sample_path = os.path.join(output_dir, f"{speaker}_voice_sample.mp3")
                combined.export(sample_path, format="mp3")
                voice_samples[speaker] = sample_path
                print(f"Extracted {len(combined)/1000:.2f}s of audio for {speaker}")

        return voice_samples

    def clone_voice(self, name: str, sample_path: str) -> str:
        """
        Clone a voice using ElevenLabs IVC API.

        Args:
            name: Name for the cloned voice
            sample_path: Path to the voice sample audio file

        Returns:
            Voice ID of the cloned voice
        """
        print(f"Cloning voice '{name}' from {sample_path}...")

        with open(sample_path, "rb") as f:
            voice = self.client.voices.ivc.create(
                name=name,
                files=[BytesIO(f.read())]
            )

        print(f"Cloned voice '{name}' with voice ID: {voice.voice_id}")
        return voice.voice_id

    def clone_voices_from_samples(
        self,
        voice_samples: Dict[str, str],
        name_prefix: str = "Cloned"
    ) -> Dict[str, str]:
        """
        Clone voices for all speakers from their sample files.

        Args:
            voice_samples: Dictionary mapping speaker labels to sample file paths
            name_prefix: Prefix for cloned voice names

        Returns:
            Dictionary mapping speaker labels to voice IDs
        """
        voice_mapping = {}

        for speaker, sample_path in voice_samples.items():
            try:
                voice_id = self.clone_voice(
                    name=f"{name_prefix}_{speaker}",
                    sample_path=sample_path
                )
                voice_mapping[speaker] = voice_id
            except Exception as e:
                print(f"Warning: Failed to clone voice for {speaker}: {e}")

        return voice_mapping

    def clone_voices_from_transcript(
        self,
        audio_path: str,
        transcript_segments: List[Dict],
        output_dir: Optional[str] = None,
        name_prefix: str = "Cloned"
    ) -> Dict[str, str]:
        """
        Complete voice cloning pipeline from audio and transcript.

        Args:
            audio_path: Path to the audio file
            transcript_segments: List of transcript segments with speaker info
            output_dir: Directory to save intermediate voice samples
            name_prefix: Prefix for cloned voice names

        Returns:
            Dictionary mapping speaker labels to cloned voice IDs
        """
        # Load audio
        audio_format = Path(audio_path).suffix.lstrip('.')
        audio = AudioSegment.from_file(audio_path, format=audio_format)

        # Extract speaker clips
        speaker_clips = self.extract_speaker_clips(audio, transcript_segments)

        if not speaker_clips:
            print("No speaker segments found in transcript")
            return {}

        # Combine clips into voice samples
        voice_samples = self.combine_speaker_clips(
            speaker_clips,
            output_dir=output_dir
        )

        # Clone voices
        voice_mapping = self.clone_voices_from_samples(
            voice_samples,
            name_prefix=name_prefix
        )

        return voice_mapping

    def generate_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2"
    ) -> Generator[bytes, None, None]:
        """
        Generate speech audio from text using a specific voice.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID to use
            model_id: Model ID for TTS

        Returns:
            Generator yielding audio bytes
        """
        return self.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.0,
                use_speaker_boost=True
            )
        )

    def generate_speech_to_file(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        model_id: str = "eleven_multilingual_v2"
    ) -> str:
        """
        Generate speech audio from text and save to file.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID to use
            output_path: Path to save the audio file
            model_id: Model ID for TTS

        Returns:
            Path to the saved audio file
        """
        audio_generator = self.generate_speech(text, voice_id, model_id)

        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        return output_path


def get_voice_id_for_speaker(
    speaker: str,
    voice_mapping: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Get voice ID for a speaker, falling back to environment variable.

    Args:
        speaker: Speaker label
        voice_mapping: Optional mapping of speaker labels to voice IDs

    Returns:
        Voice ID or None if not found
    """
    # First check environment variable
    env_voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    if env_voice_id:
        return env_voice_id

    # Then check voice mapping
    if voice_mapping and speaker in voice_mapping:
        return voice_mapping[speaker]

    return None


def should_clone_voices() -> bool:
    """
    Check if voice cloning should be performed.

    Voice cloning is performed only if ELEVENLABS_VOICE_ID is not set.

    Returns:
        True if voice cloning should be performed
    """
    return os.getenv('ELEVENLABS_VOICE_ID') is None
