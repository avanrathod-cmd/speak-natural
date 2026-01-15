"""
Unified audio processing service.

Handles the complete pipeline:
1. Upload audio to S3
2. Transcribe audio using AWS Transcribe
3. Run full vocal analysis and coaching
4. Upload all results to S3
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Optional
import tempfile
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from speach_to_text.transcribe import read_transcription, transcribe_audio_from_s3
from vocal_analysis.run_full_coaching import run_full_coaching_pipeline
from utils.aws_utils import s3_client
from services.metrics_generator import generate_structured_metrics


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

    def transcribe_audio(self, s3_uri: str, job_name: str) -> Dict:
        """
        Transcribe audio from S3 using AWS Transcribe.

        Args:
            s3_uri: S3 URI of the audio file
            job_name: Unique transcription job name

        Returns:
            Transcription data as dict
        """
        print(f"Starting transcription job: {job_name}")
        print(f"Audio URI: {s3_uri}")

        transcription_data = read_transcription(job_name, s3_uri)

        print(f"✓ Transcription complete")
        return transcription_data

    def save_transcript_to_file(self, transcript_data: Dict, output_path: str) -> str:
        """
        Save transcription data to JSON file.

        Args:
            transcript_data: Transcription data dictionary
            output_path: Path to save JSON file

        Returns:
            Path to saved file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)

        print(f"✓ Transcript saved to: {output_path}")
        return output_path

    def upload_file_to_s3(self, local_path: str, s3_key: str) -> str:
        """
        Upload any file to S3.

        Args:
            local_path: Local file path
            s3_key: S3 object key

        Returns:
            S3 URI
        """
        with open(local_path, 'rb') as f:
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=f
            )

        return f"s3://{self.bucket_name}/{s3_key}"

    def upload_directory_to_s3(self, local_dir: str, s3_prefix: str) -> Dict[str, str]:
        """
        Upload all files in a directory to S3.

        Args:
            local_dir: Local directory path
            s3_prefix: S3 prefix (folder path)

        Returns:
            Dictionary mapping local paths to S3 URIs
        """
        uploaded_files = {}
        local_dir_path = Path(local_dir)

        for file_path in local_dir_path.rglob('*'):
            if file_path.is_file():
                # Get relative path from local_dir
                relative_path = file_path.relative_to(local_dir_path)
                s3_key = f"{s3_prefix}/{relative_path}"

                s3_uri = self.upload_file_to_s3(str(file_path), s3_key)
                uploaded_files[str(file_path)] = s3_uri

        print(f"✓ Uploaded {len(uploaded_files)} files to S3 under {s3_prefix}/")
        return uploaded_files

    def run_vocal_analysis(
        self,
        transcript_path: str,
        audio_path: str,
        output_dir: str,
        skip_coaching: bool = False
    ) -> Dict:
        """
        Run full vocal analysis and coaching pipeline.

        Args:
            transcript_path: Path to transcript JSON
            audio_path: Path to audio WAV file
            output_dir: Output directory for results
            skip_coaching: Skip AI coaching generation

        Returns:
            Dictionary with paths to output files
        """
        print("=" * 80)
        print("Running vocal analysis and coaching pipeline...")
        print("=" * 80)

        results = run_full_coaching_pipeline(
            transcript_path=transcript_path,
            audio_path=audio_path,
            output_dir=output_dir,
            skip_coaching=skip_coaching
        )

        return results

    def process_audio_file(
        self,
        audio_file_path: str,
        request_id: str,
        output_base_dir: str = "/tmp/speak-right",
        skip_coaching: bool = False
    ) -> Dict:
        """
        Complete end-to-end processing of an audio file.

        Steps:
        1. Upload audio to S3
        2. Transcribe audio
        3. Save transcript locally and to S3
        4. Run vocal analysis
        5. Upload all results to S3

        Args:
            audio_file_path: Local path to audio file
            request_id: Unique request ID
            output_base_dir: Base directory for local outputs
            skip_coaching: Skip AI coaching generation

        Returns:
            Dictionary with all output paths and S3 URIs
        """
        # Create request-specific directories
        request_dir = os.path.join(output_base_dir, request_id)
        os.makedirs(request_dir, exist_ok=True)

        audio_filename = Path(audio_file_path).name
        audio_stem = Path(audio_file_path).stem

        # S3 keys
        s3_audio_key = f"{request_id}/input/{audio_filename}"
        s3_transcript_key = f"{request_id}/transcript/{audio_stem}_transcript.json"

        print("=" * 80)
        print(f"PROCESSING REQUEST: {request_id}")
        print("=" * 80)

        # Step 1: Upload audio to S3
        print("\n[1/5] Uploading audio to S3...")
        s3_audio_uri = self.upload_audio_to_s3(audio_file_path, s3_audio_key)

        # Step 2: Transcribe audio
        print("\n[2/5] Transcribing audio...")
        job_name = f"job-{request_id}"
        transcript_data = self.transcribe_audio(s3_audio_uri, job_name)

        # Step 3: Save transcript
        print("\n[3/5] Saving transcript...")
        local_transcript_path = os.path.join(request_dir, "transcript.json")
        self.save_transcript_to_file(transcript_data, local_transcript_path)

        s3_transcript_uri = self.upload_file_to_s3(local_transcript_path, s3_transcript_key)

        # Step 4: Run vocal analysis
        print("\n[4/6] Running vocal analysis and coaching...")
        analysis_output_dir = os.path.join(request_dir, "output")

        analysis_results = self.run_vocal_analysis(
            transcript_path=local_transcript_path,
            audio_path=audio_file_path,
            output_dir=analysis_output_dir,
            skip_coaching=skip_coaching
        )

        # Step 5: Generate structured metrics
        print("\n[5/6] Generating structured metrics...")
        coaching_analysis_path = analysis_results.get("analysis")
        coaching_feedback_path = analysis_results.get("coaching_feedback")

        if coaching_analysis_path and os.path.exists(coaching_analysis_path):
            try:
                structured_metrics = generate_structured_metrics(
                    coaching_analysis_path=coaching_analysis_path,
                    coaching_feedback_path=coaching_feedback_path if coaching_feedback_path and os.path.exists(coaching_feedback_path) else None
                )

                # Save structured metrics
                metrics_path = os.path.join(analysis_output_dir, "metrics", "structured_metrics.json")
                os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

                with open(metrics_path, 'w') as f:
                    json.dump(structured_metrics, f, indent=2)

                print(f"✓ Structured metrics saved to: {metrics_path}")
                print(f"  Overall Score: {structured_metrics['overall_score']}/10")
                print(f"  Pace: {structured_metrics['pace']['rating']}")
                print(f"  Pitch Variation: {structured_metrics['pitch_variation']['rating']}")
                print(f"  Energy Level: {structured_metrics['energy_level']['rating']}")

                analysis_results["structured_metrics"] = metrics_path

            except Exception as e:
                print(f"⚠ Warning: Could not generate structured metrics: {e}")
                import traceback
                traceback.print_exc()

        # Step 6: Upload all results to S3
        print("\n[6/6] Uploading results to S3...")
        s3_output_prefix = f"{request_id}/output"
        uploaded_files = self.upload_directory_to_s3(analysis_output_dir, s3_output_prefix)

        print("\n" + "=" * 80)
        print(f"✅ PROCESSING COMPLETE: {request_id}")
        print("=" * 80)

        return {
            "request_id": request_id,
            "status": "completed",
            "input": {
                "audio_file": audio_file_path,
                "s3_audio_uri": s3_audio_uri
            },
            "transcript": {
                "local_path": local_transcript_path,
                "s3_uri": s3_transcript_uri
            },
            "analysis": analysis_results,
            "s3_outputs": uploaded_files,
            "local_output_dir": analysis_output_dir
        }


def process_audio_simple(
    audio_file_path: str,
    request_id: Optional[str] = None,
    bucket_name: str = "speach-analyzer",
    skip_coaching: bool = False
) -> Dict:
    """
    Simple function to process an audio file.

    Args:
        audio_file_path: Path to audio file
        request_id: Optional request ID (generated if not provided)
        bucket_name: S3 bucket name
        skip_coaching: Skip AI coaching

    Returns:
        Processing results dictionary
    """
    import uuid

    if request_id is None:
        request_id = str(uuid.uuid4())

    processor = AudioProcessorService(bucket_name=bucket_name)
    results = processor.process_audio_file(
        audio_file_path=audio_file_path,
        request_id=request_id,
        skip_coaching=skip_coaching
    )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process audio file through complete coaching pipeline")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("--request-id", help="Request ID (optional, will be generated if not provided)")
    parser.add_argument("--bucket", default="speach-analyzer", help="S3 bucket name")
    parser.add_argument("--skip-coaching", action="store_true", help="Skip AI coaching generation")

    args = parser.parse_args()

    results = process_audio_simple(
        audio_file_path=args.audio_file,
        request_id=args.request_id,
        bucket_name=args.bucket,
        skip_coaching=args.skip_coaching
    )

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(json.dumps(results, indent=2, default=str))
