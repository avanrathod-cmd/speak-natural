"""
Storage manager for handling request IDs and folder structures.
Now uses Supabase PostgreSQL for metadata storage.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import shutil
from api.database import DatabaseService
from utils.s3_paths import get_path_manager, get_audio_stem
from utils.aws_utils import s3_client


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

        # Initialize database service for metadata storage
        self.db = DatabaseService()

        # Keep metadata directory for backward compatibility / local backup
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
        Save session metadata to Supabase database.
        Also saves to local JSON file as backup.

        Args:
            coaching_id: Coaching session ID
            metadata: Metadata dictionary (must include user_id, audio_filename)

        Returns:
            Path to metadata file (legacy)
        """
        # Extract required fields
        user_id = metadata.get("user_id")
        audio_filename = metadata.get("audio_filename")

        if not user_id or not audio_filename:
            raise ValueError("user_id and audio_filename are required in metadata")

        # Check if session exists
        existing_session = self.db.get_session(coaching_id)

        if existing_session:
            # Update existing session
            update_data = {}
            if "status" in metadata:
                update_data["status"] = metadata["status"]
            if "progress" in metadata:
                update_data["progress"] = metadata["progress"]
            if "error" in metadata:
                update_data["error"] = metadata["error"]
            if "audio_filename" in metadata:
                update_data["audio_filename"] = metadata["audio_filename"]
            if "directories" in metadata:
                self.db.update_directories(coaching_id, metadata["directories"])
            if "voice_mapping" in metadata:
                self.db.save_voice_mapping(coaching_id, metadata["voice_mapping"])

            if update_data:
                self.db.update_session_status(
                    coaching_id,
                    status=update_data.get("status", existing_session["status"]),
                    progress=update_data.get("progress"),
                    error=update_data.get("error"),
                    audio_filename=update_data.get("audio_filename")
                )
        else:
            # Create new session
            self.db.create_session(
                coaching_id=coaching_id,
                user_id=user_id,
                audio_filename=audio_filename,
                directories=metadata.get("directories", {})
            )

        # Also save to local JSON as backup
        metadata_path = self.metadata_dir / f"{coaching_id}.json"
        if "created_at" not in metadata:
            metadata["created_at"] = datetime.now().isoformat()
        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return str(metadata_path)

    def load_session_metadata(self, coaching_id: str) -> Optional[Dict]:
        """
        Load session metadata from Supabase database.
        Falls back to JSON file if not found in database.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Metadata dictionary or None if not found
        """
        # Try loading from database first
        session = self.db.get_session(coaching_id)

        if session:
            # Convert database format to legacy format
            metadata = {
                "coaching_id": session["coaching_id"],
                "user_id": session["user_id"],
                "audio_filename": session["audio_filename"],
                "status": session["status"],
                "directories": session.get("directories", {}),
                "voice_mapping": session.get("voice_mapping"),
                "progress": session.get("progress"),
                "error": session.get("error"),
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "completed_at": session.get("completed_at"),
            }

            # Reconstruct analysis paths from directories and S3
            directories = session.get("directories", {})
            audio_filename = session["audio_filename"]

            if directories:
                analysis_dict = self._find_analysis_files(coaching_id, directories, audio_filename)
                if analysis_dict:
                    metadata["analysis"] = analysis_dict

                # Also add input paths (check S3 first, then local)
                pm = get_path_manager()
                input_key = pm.get_input_key(coaching_id, audio_filename)

                try:
                    # Check if file exists in S3
                    s3_client.head_object(Bucket=pm.bucket_name, Key=input_key)
                    # Generate presigned URL for audio file
                    audio_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': pm.bucket_name, 'Key': input_key},
                        ExpiresIn=86400
                    )
                    metadata["input"] = {
                        "wav_audio_file": audio_url,
                        "s3_key": input_key
                    }
                except:
                    # Fallback to local file
                    input_dir = directories.get("input")
                    if input_dir:
                        wav_path = os.path.join(input_dir, audio_filename)
                        if os.path.exists(wav_path):
                            metadata["input"] = {
                                "wav_audio_file": wav_path
                            }

            return metadata

        # Fallback to local JSON file (for backward compatibility)
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
        Update session status in database and local metadata.

        Args:
            coaching_id: Coaching session ID
            status: Status (pending, processing, completed, failed)
            progress: Optional progress message
            error: Optional error message
        """
        # Update in database
        self.db.update_session_status(
            coaching_id=coaching_id,
            status=status,
            progress=progress,
            error=error
        )

        # Also update local JSON for backup
        metadata = self.load_session_metadata(coaching_id) or {"coaching_id": coaching_id}
        metadata["status"] = status

        if progress:
            metadata["progress"] = progress

        if error:
            metadata["error"] = error

        if status == "completed":
            metadata["completed_at"] = datetime.now().isoformat()

        metadata_path = self.metadata_dir / f"{coaching_id}.json"
        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def save_voice_mapping(
        self,
        coaching_id: str,
        voice_mapping: Dict[str, str]
    ):
        """
        Save voice mapping (speaker -> voice_id) to database and session metadata.

        Args:
            coaching_id: Coaching session ID
            voice_mapping: Dictionary mapping speaker labels to ElevenLabs voice IDs
        """
        # Save to database
        self.db.save_voice_mapping(coaching_id, voice_mapping)

        # Also save to local JSON for backup
        metadata = self.load_session_metadata(coaching_id) or {"coaching_id": coaching_id}
        metadata["voice_mapping"] = voice_mapping
        metadata["updated_at"] = datetime.now().isoformat()

        metadata_path = self.metadata_dir / f"{coaching_id}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def get_voice_mapping(self, coaching_id: str) -> Optional[Dict[str, str]]:
        """
        Get voice mapping from database.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Dictionary mapping speaker labels to voice IDs, or None if not found
        """
        return self.db.get_voice_mapping(coaching_id)

    def cleanup_session(self, coaching_id: str, keep_metadata: bool = True):
        """
        Clean up session files from local storage and optionally database.

        Args:
            coaching_id: Coaching session ID
            keep_metadata: Whether to keep metadata in database and file
        """
        session_dir = self.base_dir / coaching_id

        if session_dir.exists():
            shutil.rmtree(session_dir)

        if not keep_metadata:
            # Delete from database
            self.db.delete_session(coaching_id)

            # Delete local JSON file
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

    def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """
        List coaching sessions from database.
        If user_id is provided, lists only that user's sessions.
        Otherwise lists all sessions (admin function).

        Args:
            user_id: Optional user UUID to filter by

        Returns:
            List of coaching session IDs
        """
        if user_id:
            sessions = self.db.list_user_sessions(user_id)
        else:
            sessions = self.db.list_all_sessions()

        return [session["coaching_id"] for session in sessions]

    def list_sessions_detailed(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        List coaching sessions with full metadata from database.
        If user_id is provided, lists only that user's sessions.
        Otherwise lists all sessions (admin function).

        Args:
            user_id: Optional user UUID to filter by

        Returns:
            List of session metadata dictionaries
        """
        if user_id:
            return self.db.list_user_sessions(user_id)
        else:
            return self.db.list_all_sessions()

    def _find_analysis_files(self, coaching_id: str, directories: Dict, audio_filename: str) -> Optional[Dict]:
        """
        Find analysis files from S3.

        IMPORTANT: This checks S3, not local files!
        Cloud Run is stateless - files must be in S3.

        Args:
            coaching_id: Coaching session ID
            directories: Directories dictionary from metadata (for fallback local check)
            audio_filename: Audio filename to derive stem

        Returns:
            Dictionary with S3 URLs for analysis files or None if not found
        """
        pm = get_path_manager()
        stem = get_audio_stem(audio_filename)

        analysis_dict = {}

        # Try to find files in S3 first (Cloud Run compatible)
        try:
            # Check for coaching analysis JSON
            analysis_key = pm.get_analysis_key(coaching_id, stem)
            try:
                s3_client.head_object(Bucket=pm.bucket_name, Key=analysis_key)
                # File exists - generate presigned URL (valid for 24 hours)
                analysis_dict["analysis"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': pm.bucket_name, 'Key': analysis_key},
                    ExpiresIn=86400
                )
            except:
                pass  # File doesn't exist in S3

            # Check for coaching feedback
            feedback_key = pm.get_coaching_feedback_key(coaching_id, stem)
            try:
                s3_client.head_object(Bucket=pm.bucket_name, Key=feedback_key)
                analysis_dict["coaching_feedback"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': pm.bucket_name, 'Key': feedback_key},
                    ExpiresIn=86400
                )
            except:
                pass

            # Check for prosody data
            prosody_key = pm.get_prosody_data_key(coaching_id, stem)
            try:
                s3_client.head_object(Bucket=pm.bucket_name, Key=prosody_key)
                analysis_dict["prosody_data"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': pm.bucket_name, 'Key': prosody_key},
                    ExpiresIn=86400
                )
            except:
                pass

            # For visualizations, just store the prefix (we can list when needed)
            viz_prefix = pm.get_visualizations_prefix(coaching_id)
            analysis_dict["visualizations"] = viz_prefix

        except Exception as e:
            print(f"Error checking S3 for analysis files: {e}")

        # Fallback: Check local files (for development/testing)
        if not analysis_dict:
            from glob import glob

            # Find coaching analysis JSON
            analysis_dir = directories.get("analysis")
            if analysis_dir and os.path.exists(analysis_dir):
                json_files = glob(os.path.join(analysis_dir, "*_coaching_analysis.json"))
                if json_files:
                    analysis_dict["analysis"] = json_files[0]

            # Find coaching feedback markdown
            coaching_dir = directories.get("coaching")
            if coaching_dir and os.path.exists(coaching_dir):
                md_files = glob(os.path.join(coaching_dir, "*_coaching_feedback.md"))
                if md_files:
                    analysis_dict["coaching_feedback"] = md_files[0]

            # Find visualizations directory
            viz_dir = directories.get("visualizations")
            if viz_dir and os.path.exists(viz_dir):
                analysis_dict["visualizations"] = viz_dir

            # Find prosody data if exists
            if coaching_dir and os.path.exists(coaching_dir):
                prosody_files = glob(os.path.join(coaching_dir, "*_prosody_data.txt"))
                if prosody_files:
                    analysis_dict["prosody_data"] = prosody_files[0]

        return analysis_dict if analysis_dict else None

    def ensure_local_file(self, file_path_or_url: str, coaching_id: str, file_type: str) -> str:
        """
        Ensure file is available locally, downloading from S3 if needed.

        This is critical for Cloud Run - files may be S3 URLs that need downloading.

        Args:
            file_path_or_url: Either a local path or S3 presigned URL
            coaching_id: Coaching session ID (for temp path)
            file_type: Type of file (for temp filename)

        Returns:
            Local file path

        Example:
            # Input could be local path
            path = ensure_local_file("/tmp/file.json", "coach_123", "analysis")
            # Or S3 URL (will download to temp)
            path = ensure_local_file("https://s3.amazonaws.com/...", "coach_123", "analysis")
        """
        import tempfile
        import requests

        # If it's already a local file that exists, return it
        if not file_path_or_url.startswith("http") and os.path.exists(file_path_or_url):
            return file_path_or_url

        # It's an S3 URL - download to temp file
        if file_path_or_url.startswith("http"):
            # Create temp file
            temp_dir = os.path.join(tempfile.gettempdir(), "speak-right", coaching_id)
            os.makedirs(temp_dir, exist_ok=True)

            # Determine extension from file_type
            ext_map = {
                "analysis": ".json",
                "coaching_feedback": ".md",
                "prosody_data": ".txt",
                "transcript": ".json",
                "audio": ".wav"
            }
            ext = ext_map.get(file_type, ".tmp")

            temp_path = os.path.join(temp_dir, f"{file_type}{ext}")

            # Download file
            print(f"Downloading {file_type} from S3 to {temp_path}")
            response = requests.get(file_path_or_url, timeout=60)
            response.raise_for_status()

            with open(temp_path, 'wb') as f:
                f.write(response.content)

            return temp_path

        # Neither local nor URL - raise error
        raise FileNotFoundError(f"File not found: {file_path_or_url}")

    def get_s3_prefix(self, coaching_id: str) -> str:
        """
        Get S3 prefix for a coaching session.

        Args:
            coaching_id: Coaching session ID

        Returns:
            S3 prefix string
        """
        return f"coaching_sessions/{coaching_id}"
