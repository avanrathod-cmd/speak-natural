"""
Audio processing utilities for the sales call pipeline.

Handles:
1. WAV format conversion (ffmpeg)
2. S3 upload
3. Deepgram transcription
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Tuple
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
sys.stdout.reconfigure(line_buffering=True)
logger = logging.getLogger("speak-right.processor")

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from utils.aws_utils import s3_client
from utils.deepgram_client import transcribe_from_s3
from models.transcript import Transcript


def _is_valid_wav(file_path: str) -> bool:
    """Check if a file is a valid WAV audio file by examining its header."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(12)
            # WAV files start with "RIFF" and contain "WAVE" at bytes 8-12
            return (
                len(header) >= 12 and
                header[:4] == b'RIFF' and
                header[8:12] == b'WAVE'
            )
    except (IOError, OSError):
        return False


def _convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    Convert an audio file to WAV format using ffmpeg.

    Args:
        input_path: Path to the input audio file
        output_path: Path for the output WAV file

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-y', '-i', input_path,
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            os.remove(input_path)
            return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Error converting audio: {e}")
        return False


def ensure_wav_format(audio_file_path: str) -> Tuple[str, bool]:
    """
    Ensure the audio file is in WAV format, converting if necessary.

    Args:
        audio_file_path: Path to the audio file

    Returns:
        Tuple of (path_to_wav_file, was_converted)
        If conversion fails, raises an exception.
    """
    if _is_valid_wav(audio_file_path):
        return audio_file_path, False

    # Need to convert - create a temp WAV file
    input_path = Path(audio_file_path)
    wav_path = str(input_path.with_suffix('.wav'))

    # If the output would overwrite the input, use a temp file
    if wav_path == audio_file_path:
        wav_path = str(input_path.with_stem(input_path.stem + '_converted').with_suffix('.wav'))

    print(f"Converting {audio_file_path} to WAV format...")

    if not _convert_to_wav(audio_file_path, wav_path):
        raise RuntimeError(f"Failed to convert {audio_file_path} to WAV format. Ensure ffmpeg is installed.")

    print(f"✓ Converted to: {wav_path}")
    return wav_path, True


class AudioProcessorService:
    """Service for processing audio files through the complete coaching pipeline."""

    def __init__(self, bucket_name: str = "speach-analyzer"):
        """
        Initialize the audio processor service.

        Args:
            bucket_name: S3 bucket name for storage
        """
        self.bucket_name = bucket_name

    def upload_audio_to_s3(self, audio_file_path: str, s3_key: str) -> str:
        """
        Upload audio file to S3.

        Args:
            audio_file_path: Local path to audio file
            s3_key: S3 object key (path in bucket)

        Returns:
            S3 URI of the uploaded file
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        print(f"Uploading {audio_file_path} to s3://{self.bucket_name}/{s3_key}...")

        with open(audio_file_path, 'rb') as file_data:
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data
            )

        s3_uri = f"s3://{self.bucket_name}/{s3_key}"
        print(f"✓ Upload complete: {s3_uri}")
        return s3_uri

    def transcribe_audio(self, s3_uri: str, job_name: str) -> Transcript:
        """
        Transcribe audio from S3 using Deepgram Nova-2.

        Args:
            s3_uri: S3 URI of the audio file
            job_name: Identifier used only for logging (no async job needed)

        Returns:
            Typed Transcript
        """
        print(f"Transcribing: {s3_uri}")
        transcript = transcribe_from_s3(s3_uri)
        print("✓ Transcription complete")
        return transcript

