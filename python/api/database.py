"""
Database service for Supabase PostgreSQL operations.
Handles coaching session metadata storage.
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class DatabaseService:
    """Manages Supabase database operations for coaching sessions."""

    def __init__(self):
        """Initialize Supabase client with service role key (admin access)."""
        supabase_url = os.getenv("SUPABASE_URL")
        # Use service_role key for admin access (bypasses RLS)
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment"
            )

        # Create client with service role (admin privileges)
        self.client: Client = create_client(supabase_url, service_role_key)

    def create_session(
        self,
        coaching_id: str,
        user_id: str,
        audio_filename: str,
        directories: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new coaching session in the database.

        Args:
            coaching_id: Unique coaching session ID
            user_id: User UUID from JWT
            audio_filename: Original audio filename
            directories: Optional directory paths

        Returns:
            Created session data
        """
        data = {
            "coaching_id": coaching_id,
            "user_id": user_id,
            "audio_filename": audio_filename,
            "status": "pending",
            "directories": directories or {},
        }

        result = self.client.table("coaching_sessions").insert(data).execute()

        if not result.data:
            raise Exception("Failed to create session in database")

        return result.data[0]

    def get_session(self, coaching_id: str) -> Optional[Dict]:
        """
        Get session metadata by coaching_id.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Session data or None if not found
        """
        result = (
            self.client.table("coaching_sessions")
            .select("*")
            .eq("coaching_id", coaching_id)
            .execute()
        )

        if result.data and len(result.data) > 0:
            return result.data[0]

        return None

    def get_session_by_user(self, coaching_id: str, user_id: str) -> Optional[Dict]:
        """
        Get session metadata by coaching_id and user_id (for authorization).

        Args:
            coaching_id: Coaching session ID
            user_id: User UUID

        Returns:
            Session data or None if not found or unauthorized
        """
        result = (
            self.client.table("coaching_sessions")
            .select("*")
            .eq("coaching_id", coaching_id)
            .eq("user_id", user_id)
            .execute()
        )

        if result.data and len(result.data) > 0:
            return result.data[0]

        return None

    def update_session_status(
        self,
        coaching_id: str,
        status: str,
        progress: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict:
        """
        Update session status and optionally progress/error.

        Args:
            coaching_id: Coaching session ID
            status: New status (pending, processing, completed, failed)
            progress: Optional progress message
            error: Optional error message

        Returns:
            Updated session data
        """
        update_data = {"status": status}

        if progress is not None:
            update_data["progress"] = progress

        if error is not None:
            update_data["error"] = error

        if status == "completed":
            update_data["completed_at"] = datetime.now().isoformat()

        result = (
            self.client.table("coaching_sessions")
            .update(update_data)
            .eq("coaching_id", coaching_id)
            .execute()
        )

        if not result.data:
            raise Exception(f"Failed to update session {coaching_id}")

        return result.data[0]

    def save_voice_mapping(
        self, coaching_id: str, voice_mapping: Dict[str, str]
    ) -> Dict:
        """
        Save voice mapping (speaker -> voice_id) to session.

        Args:
            coaching_id: Coaching session ID
            voice_mapping: Dictionary mapping speaker labels to ElevenLabs voice IDs

        Returns:
            Updated session data
        """
        result = (
            self.client.table("coaching_sessions")
            .update({"voice_mapping": voice_mapping})
            .eq("coaching_id", coaching_id)
            .execute()
        )

        if not result.data:
            raise Exception(f"Failed to save voice mapping for {coaching_id}")

        return result.data[0]

    def get_voice_mapping(self, coaching_id: str) -> Optional[Dict[str, str]]:
        """
        Get voice mapping from session.

        Args:
            coaching_id: Coaching session ID

        Returns:
            Voice mapping dictionary or None
        """
        session = self.get_session(coaching_id)
        if session:
            return session.get("voice_mapping")
        return None

    def list_user_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        """
        List all sessions for a user, ordered by creation date (newest first).

        Args:
            user_id: User UUID
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            List of session data
        """
        result = (
            self.client.table("coaching_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )

        return result.data or []

    def list_all_sessions(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        List all sessions (admin function).

        Args:
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            List of session data
        """
        result = (
            self.client.table("coaching_sessions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )

        return result.data or []

    def delete_session(self, coaching_id: str) -> bool:
        """
        Delete a session from the database.

        Args:
            coaching_id: Coaching session ID

        Returns:
            True if deleted successfully
        """
        result = (
            self.client.table("coaching_sessions")
            .delete()
            .eq("coaching_id", coaching_id)
            .execute()
        )

        return bool(result.data)

    def update_directories(self, coaching_id: str, directories: Dict) -> Dict:
        """
        Update directory paths for a session.

        Args:
            coaching_id: Coaching session ID
            directories: Dictionary of directory paths

        Returns:
            Updated session data
        """
        result = (
            self.client.table("coaching_sessions")
            .update({"directories": directories})
            .eq("coaching_id", coaching_id)
            .execute()
        )

        if not result.data:
            raise Exception(f"Failed to update directories for {coaching_id}")

        return result.data[0]
