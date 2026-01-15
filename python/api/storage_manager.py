"""
Storage manager for handling request IDs and folder structures.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import shutil


class StorageManager:
    """Manages local and S3 storage for coaching sessions."""

    def __init__(self, base_dir: str = "/tmp/speak-right"):
        """
        Initialize storage manager.

        Args:
            base_dir: Base directory for local storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata directory
        self.metadata_dir = self.base_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)

    def generate_coaching_id(self) -> str:
        """
        Generate a unique coaching session ID.

        Returns:
            Unique coaching ID
        """
        return f"coach_{uuid.uuid4().hex[:12]}"

    def create_session_directory(self, coaching_id: str) -> Dict[str, str]:
        """
        Create directory structure for a coaching session.

        Structure:
        {base_dir}/
            {coaching_id}/
                input/          # Original audio file
                transcript/     # Transcript JSON
                output/         # Analysis results
                    analysis/
                    visualizations/
                    coaching/

        Args:
            coaching_id: Coaching session ID

        Returns:
            Dictionary with paths to directories
        """
        session_dir = self.base_dir / coaching_id

        directories = {
            "root": str(session_dir),
            "input": str(session_dir / "input"),
            "transcript": str(session_dir / "transcript"),
            "output": str(session_dir / "output"),
            "analysis": str(session_dir / "output" / "analysis"),
            "visualizations": str(session_dir / "output" / "visualizations"),
            "coaching": str(session_dir / "output" / "coaching"),
        }

        # Create all directories
        for dir_path in directories.values():
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        return directories

    def save_session_metadata(self, coaching_id: str, metadata: Dict) -> str:
        """
        Save session metadata to JSON file.

        Args:
            coaching_id: Coaching session ID
            metadata: Metadata dictionary

        Returns:
            Path to metadata file
        """
        metadata_path = self.metadata_dir / f"{coaching_id}.json"

        # Add timestamps
        if "created_at" not in metadata:
            metadata["created_at"] = datetime.now().isoformat()

        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return str(metadata_path)

    def load_session_metadata(self, coaching_id: str) -> Optional[Dict]:
        """
        Load session metadata from JSON file.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = self.metadata_dir / f"{coaching_id}.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r') as f:
            return json.load(f)

    def update_session_status(
        self,
        coaching_id: str,
        status: str,
        progress: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update session status in metadata.

        Args:
            coaching_id: Coaching session ID
            status: Status (pending, processing, completed, failed)
            progress: Optional progress message
            error: Optional error message
        """
        metadata = self.load_session_metadata(coaching_id) or {"coaching_id": coaching_id}

        metadata["status"] = status

        if progress:
            metadata["progress"] = progress

        if error:
            metadata["error"] = error

        if status == "completed":
            metadata["completed_at"] = datetime.now().isoformat()

        self.save_session_metadata(coaching_id, metadata)

    def cleanup_session(self, coaching_id: str, keep_metadata: bool = True):
        """
        Clean up session files from local storage.

        Args:
            coaching_id: Coaching session ID
            keep_metadata: Whether to keep metadata file
        """
        session_dir = self.base_dir / coaching_id

        if session_dir.exists():
            shutil.rmtree(session_dir)

        if not keep_metadata:
            metadata_path = self.metadata_dir / f"{coaching_id}.json"
            if metadata_path.exists():
                metadata_path.unlink()

    def get_session_directory(self, coaching_id: str) -> Optional[str]:
        """
        Get session directory path if it exists.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Session directory path or None
        """
        session_dir = self.base_dir / coaching_id

        if session_dir.exists():
            return str(session_dir)

        return None

    def list_sessions(self) -> list:
        """
        List all coaching sessions.

        Returns:
            List of coaching session IDs
        """
        return [
            f.stem for f in self.metadata_dir.glob("*.json")
        ]

    def get_s3_prefix(self, coaching_id: str) -> str:
        """
        Get S3 prefix for a coaching session.

        Args:
            coaching_id: Coaching session ID

        Returns:
            S3 prefix string
        """
        return f"coaching_sessions/{coaching_id}"
