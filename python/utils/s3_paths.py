"""
Centralized S3 path utilities for SpeakRight.

This module provides a single source of truth for S3 paths and file locations.
All file operations should use these utilities instead of hardcoding paths.

Design:
- Everything lives in S3 under: s3://bucket/{coaching_id}/
- Local files are temporary during processing only
- Cloud Run is stateless - always fetch from S3 when needed
"""

import os
from typing import Optional, Dict, List
from pathlib import Path


class S3PathManager:
    """
    Centralized manager for S3 paths and file locations.

    S3 Structure:
    s3://bucket/
      {coaching_id}/
        input/
          {filename}.wav
        transcript/
          transcript.json
        output/
          analysis/
            {stem}_coaching_analysis.json
          coaching/
            {stem}_coaching_feedback.md
            {stem}_prosody_data.txt
          visualizations/
            *.svg
          metrics/
            structured_metrics.json
          segments/
            original/
              segment_{n}.wav
            improved/
              segment_{n}.wav
            segments_{max}.json
          waveform/
            waveform_{samples}.json
    """

    def __init__(self, bucket_name: str):
        """
        Initialize S3 path manager.

        Args:
            bucket_name: S3 bucket name
        """
        self.bucket_name = bucket_name

    # =========================================================================
    # S3 Key Generation
    # =========================================================================

    def get_base_key(self, coaching_id: str) -> str:
        """Get base S3 key prefix for a coaching session."""
        return f"{coaching_id}/"

    def get_input_key(self, coaching_id: str, filename: str) -> str:
        """Get S3 key for input audio file."""
        return f"{coaching_id}/input/{filename}"

    def get_transcript_key(self, coaching_id: str) -> str:
        """Get S3 key for transcript JSON."""
        return f"{coaching_id}/transcript/transcript.json"

    def get_analysis_key(self, coaching_id: str, stem: str) -> str:
        """Get S3 key for coaching analysis JSON."""
        return f"{coaching_id}/output/analysis/{stem}_coaching_analysis.json"

    def get_coaching_feedback_key(self, coaching_id: str, stem: str) -> str:
        """Get S3 key for coaching feedback markdown."""
        return f"{coaching_id}/output/coaching/{stem}_coaching_feedback.md"

    def get_prosody_data_key(self, coaching_id: str, stem: str) -> str:
        """Get S3 key for prosody data text."""
        return f"{coaching_id}/output/coaching/{stem}_prosody_data.txt"

    def get_visualization_key(self, coaching_id: str, viz_filename: str) -> str:
        """Get S3 key for visualization file."""
        return f"{coaching_id}/output/visualizations/{viz_filename}"

    def get_metrics_key(self, coaching_id: str) -> str:
        """Get S3 key for structured metrics JSON."""
        return f"{coaching_id}/output/metrics/structured_metrics.json"

    def get_segment_original_key(self, coaching_id: str, segment_id: int) -> str:
        """Get S3 key for original segment audio."""
        return f"{coaching_id}/output/segments/original/segment_{segment_id}.wav"

    def get_segment_improved_key(self, coaching_id: str, segment_id: int) -> str:
        """Get S3 key for improved segment audio."""
        return f"{coaching_id}/output/segments/improved/segment_{segment_id}.wav"

    def get_segments_cache_key(self, coaching_id: str, max_segments: int) -> str:
        """Get S3 key for segments cache JSON."""
        return f"{coaching_id}/output/segments/segments_{max_segments}.json"

    def get_waveform_cache_key(self, coaching_id: str, samples: int) -> str:
        """Get S3 key for waveform cache JSON."""
        return f"{coaching_id}/output/waveform/waveform_{samples}.json"

    # =========================================================================
    # S3 URI Generation
    # =========================================================================

    def get_s3_uri(self, key: str) -> str:
        """Convert S3 key to full s3:// URI."""
        return f"s3://{self.bucket_name}/{key}"

    # =========================================================================
    # File Discovery (for finding files when exact name not known)
    # =========================================================================

    def get_analysis_prefix(self, coaching_id: str) -> str:
        """Get S3 prefix for listing analysis files."""
        return f"{coaching_id}/output/analysis/"

    def get_coaching_prefix(self, coaching_id: str) -> str:
        """Get S3 prefix for listing coaching files."""
        return f"{coaching_id}/output/coaching/"

    def get_visualizations_prefix(self, coaching_id: str) -> str:
        """Get S3 prefix for listing visualization files."""
        return f"{coaching_id}/output/visualizations/"

    # =========================================================================
    # Local Temporary Paths (for processing only)
    # =========================================================================

    def get_local_temp_dir(self, coaching_id: str, base_dir: str = "/tmp/speak-right") -> str:
        """
        Get local temporary directory for processing.

        WARNING: These files are ephemeral on Cloud Run!
        Only use for temporary processing, then upload to S3.
        """
        return os.path.join(base_dir, coaching_id)

    def get_local_input_dir(self, coaching_id: str, base_dir: str = "/tmp/speak-right") -> str:
        """Get local input directory."""
        return os.path.join(base_dir, coaching_id, "input")

    def get_local_output_dir(self, coaching_id: str, base_dir: str = "/tmp/speak-right") -> str:
        """Get local output directory."""
        return os.path.join(base_dir, coaching_id, "output")


def get_audio_stem(filename: str) -> str:
    """
    Get stem (filename without extension) from audio filename.

    Args:
        filename: Audio filename (e.g., "00-00_00-15.wav")

    Returns:
        Stem (e.g., "00-00_00-15")
    """
    return Path(filename).stem


# Global instance (initialized with bucket from env)
_path_manager: Optional[S3PathManager] = None


def get_path_manager() -> S3PathManager:
    """
    Get global S3PathManager instance.

    Returns:
        Singleton S3PathManager instance
    """
    global _path_manager
    if _path_manager is None:
        bucket_name = os.getenv("S3_BUCKET", "speach-analyzer")
        _path_manager = S3PathManager(bucket_name)
    return _path_manager


# Convenience functions using global instance
def get_s3_key(coaching_id: str, file_type: str, **kwargs) -> str:
    """
    Get S3 key for a specific file type.

    Args:
        coaching_id: Coaching session ID
        file_type: Type of file (e.g., "analysis", "coaching_feedback", "transcript")
        **kwargs: Additional parameters (e.g., stem, segment_id)

    Returns:
        S3 key

    Examples:
        get_s3_key("coach_123", "analysis", stem="audio")
        get_s3_key("coach_123", "segment_original", segment_id=1)
    """
    pm = get_path_manager()

    if file_type == "analysis":
        return pm.get_analysis_key(coaching_id, kwargs["stem"])
    elif file_type == "coaching_feedback":
        return pm.get_coaching_feedback_key(coaching_id, kwargs["stem"])
    elif file_type == "prosody_data":
        return pm.get_prosody_data_key(coaching_id, kwargs["stem"])
    elif file_type == "transcript":
        return pm.get_transcript_key(coaching_id)
    elif file_type == "metrics":
        return pm.get_metrics_key(coaching_id)
    elif file_type == "segment_original":
        return pm.get_segment_original_key(coaching_id, kwargs["segment_id"])
    elif file_type == "segment_improved":
        return pm.get_segment_improved_key(coaching_id, kwargs["segment_id"])
    elif file_type == "segments_cache":
        return pm.get_segments_cache_key(coaching_id, kwargs["max_segments"])
    elif file_type == "waveform_cache":
        return pm.get_waveform_cache_key(coaching_id, kwargs["samples"])
    elif file_type == "input":
        return pm.get_input_key(coaching_id, kwargs["filename"])
    elif file_type == "visualization":
        return pm.get_visualization_key(coaching_id, kwargs["viz_filename"])
    else:
        raise ValueError(f"Unknown file_type: {file_type}")
