"""
Database service for Supabase PostgreSQL operations.
Handles coaching session metadata storage.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class DatabaseService:
    """Manages Supabase database operations for coaching sessions."""

    def __init__(self):
        """Initialize Supabase client with service role key."""
        supabase_url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "must be set in environment"
            )

        self.client: Client = create_client(
            supabase_url, service_role_key
        )

    # TODO: rename to create_coaching_session
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

        result = (
            self.client.table("coaching_sessions")
            .insert(data)
            .execute()
        )

        if not result.data:
            raise Exception("Failed to create session in database")

        return result.data[0]

    # TODO: rename to get_coaching_session
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

    # TODO: rename to get_coaching_session_by_user
    def get_session_by_user(
        self, coaching_id: str, user_id: str
    ) -> Optional[Dict]:
        """
        Get session by coaching_id and user_id (for authorization).

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

    # TODO: rename to update_coaching_session_status
    def update_session_status(
        self,
        coaching_id: str,
        status: str,
        progress: Optional[str] = None,
        error: Optional[str] = None,
        audio_filename: Optional[str] = None,
    ) -> Dict:
        """
        Update session status and optionally other fields.

        Args:
            coaching_id: Coaching session ID
            status: New status (pending, processing, completed, failed)
            progress: Optional progress message
            error: Optional error message
            audio_filename: Optional updated audio filename

        Returns:
            Updated session data
        """
        update_data = {"status": status}

        if progress is not None:
            update_data["progress"] = progress

        if error is not None:
            update_data["error"] = error

        if audio_filename is not None:
            update_data["audio_filename"] = audio_filename

        if status == "completed":
            update_data["completed_at"] = datetime.now().isoformat()

        result = (
            self.client.table("coaching_sessions")
            .update(update_data)
            .eq("coaching_id", coaching_id)
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to update session {coaching_id}"
            )

        return result.data[0]

    # TODO: rename to save_coaching_session_voice_mapping
    def save_voice_mapping(
        self, coaching_id: str, voice_mapping: Dict[str, str]
    ) -> Dict:
        """
        Save voice mapping (speaker -> voice_id) to session.

        Args:
            coaching_id: Coaching session ID
            voice_mapping: Dict mapping speaker labels to voice IDs

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
            raise Exception(
                f"Failed to save voice mapping for {coaching_id}"
            )

        return result.data[0]

    # TODO: rename to get_coaching_session_voice_mapping
    def get_voice_mapping(
        self, coaching_id: str
    ) -> Optional[Dict[str, str]]:
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

    # TODO: rename to list_coaching_sessions_by_user
    def list_user_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        """
        List all sessions for a user, newest first.

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

    # TODO: rename to list_all_coaching_sessions
    def list_all_sessions(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
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

    # TODO: rename to delete_coaching_session
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

    # TODO: rename to update_coaching_session_directories
    def update_directories(
        self, coaching_id: str, directories: Dict
    ) -> Dict:
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
            raise Exception(
                f"Failed to update directories for {coaching_id}"
            )

        return result.data[0]


# ---------------------------------------------------------------------------
# Sales Analyzer database methods
# ---------------------------------------------------------------------------

class SalesDatabaseService(DatabaseService):
    """Extends DatabaseService with sales analyzer operations."""

    def _ensure_org(self, user_id: str) -> str:
        """
        Return the org_id for a user, creating one if needed.

        Called internally before any write operation that requires
        an org. Never exposed as an API endpoint.

        Args:
            user_id: User UUID from JWT

        Returns:
            org_id (UUID string)
        """
        result = (
            self.client.table("user_profiles")
            .select("org_id")
            .eq("id", user_id)
            .execute()
        )

        if result.data and result.data[0].get("org_id"):
            return result.data[0]["org_id"]

        org_result = (
            self.client.table("organizations")
            .insert({"name": "My Organization"})
            .execute()
        )
        if not org_result.data:
            raise Exception("Failed to create organization")

        org_id = org_result.data[0]["id"]

        self.client.table("user_profiles").upsert({
            "id": user_id,
            "org_id": org_id,
            "role": "manager",
        }).execute()

        return org_id

    def _build_or_filter(
        self, search: str, columns: List[str]
    ) -> str:
        """
        Build a PostgREST OR filter string for ilike matching.

        Args:
            search: Search term
            columns: Column names to match against

        Returns:
            Comma-separated filter string, e.g.
            "name.ilike.%crm%,description.ilike.%crm%"
        """
        q = f"%{search}%"
        return ",".join(f"{col}.ilike.{q}" for col in columns)

    def create_product(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        customer_profile: Optional[str] = None,
        talking_points: Optional[str] = None,
    ) -> Dict:
        """
        Insert a new product row.

        Ensures an org exists for the user before inserting.

        Args:
            user_id: Creator's UUID
            name: Product name
            description: Optional product description
            customer_profile: Optional target customer persona
            talking_points: Optional key selling points

        Returns:
            Created product data
        """
        org_id = self._ensure_org(user_id)

        data = {
            "org_id": org_id,
            "created_by": user_id,
            "name": name,
            "description": description,
            "customer_profile": customer_profile,
            "talking_points": talking_points,
        }

        result = (
            self.client.table("products").insert(data).execute()
        )

        if not result.data:
            raise Exception("Failed to create product")

        return result.data[0]

    def create_sales_script(
        self,
        user_id: str,
        product_id: str,
        org_id: str,
        title: str,
        script_data: dict,
    ) -> Dict:
        """
        Insert a new sales_scripts row.

        Args:
            user_id: Creator's UUID
            product_id: Parent product UUID
            org_id: Organization UUID
            title: Script title
            script_data: Full LLM output dict

        Returns:
            Created script data
        """
        data = {
            "org_id": org_id,
            "created_by": user_id,
            "product_id": product_id,
            "title": title,
            "script_content": json.dumps(script_data),
            "key_phrases": script_data.get("key_phrases", []),
            "objection_handlers": script_data.get(
                "objection_handlers", {}
            ),
        }

        result = (
            self.client.table("sales_scripts").insert(data).execute()
        )

        if not result.data:
            raise Exception("Failed to create script")

        return result.data[0]

    def update_sales_script(
        self,
        script_id: str,
        title: str,
        script_data: dict,
    ) -> Dict:
        """
        Overwrite an existing sales_scripts row with new LLM output.

        Args:
            script_id: Script UUID to update
            title: Updated script title
            script_data: New LLM output dict

        Returns:
            Updated script data
        """
        data = {
            "title": title,
            "script_content": json.dumps(script_data),
            "key_phrases": script_data.get("key_phrases", []),
            "objection_handlers": script_data.get(
                "objection_handlers", {}
            ),
        }

        result = (
            self.client.table("sales_scripts")
            .update(data)
            .eq("id", script_id)
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to update script {script_id}"
            )

        return result.data[0]

    def get_sales_script(self, script_id: str) -> Optional[Dict]:
        """
        Fetch a sales_scripts row by id.

        Args:
            script_id: Script UUID

        Returns:
            Script data or None if not found
        """
        result = (
            self.client.table("sales_scripts")
            .select("*")
            .eq("id", script_id)
            .execute()
        )

        if result.data:
            return result.data[0]
        return None

    def get_latest_sales_script_for_product(
        self, product_id: str
    ) -> Optional[Dict]:
        """
        Fetch the most recent active script for a product.

        Args:
            product_id: Product UUID

        Returns:
            Script data or None
        """
        result = (
            self.client.table("sales_scripts")
            .select("*")
            .eq("product_id", product_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]
        return None

    def list_products(
        self,
        user_id: str,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Dict]:
        """
        List all products visible to a user (org-scoped).

        Returns an empty list if the user has no org yet.

        # TODO (post-MVP): A company may have multiple sales teams,
        # each with their own product set. Currently all users in an
        # org see the same products. To fix this properly, introduce
        # a `teams` table, assign users and products to teams, and
        # filter here by team membership. Requires DB migration +
        # UI for managers to configure team/product assignments.

        Args:
            user_id: User UUID
            search: Optional text filter across name, description,
                    customer_profile, and talking_points
            order_by: Column to sort by (default: created_at)
            order_desc: Sort descending if True (default: True)

        Returns:
            List of product rows
        """
        org_id = self._get_org_id(user_id)
        if not org_id:
            return []

        query = (
            self.client.table("products")
            .select("*")
            .eq("org_id", org_id)
        )

        if search:
            # TODO: hardcoded column list breaks when new columns are
            # added to the products table. Consider using Postgres
            # full-text search (tsvector/tsquery) or a schema-driven
            # approach where searchable columns are declared in the
            # migration, so this code never needs to change.
            query = query.or_(self._build_or_filter(
                search,
                ["name", "description",
                 "customer_profile", "talking_points"],
            ))

        query = query.order(order_by, desc=order_desc)
        return query.execute().data or []

    def create_sales_call(
        self,
        user_id: str,
        call_id: str,
        audio_filename: str,
    ) -> Dict:
        """
        Insert a new sales_calls row with status "pending".

        Args:
            user_id: UUID of the uploading user (rep_id)
            call_id: Unique call identifier (e.g. "call_abc123")
            audio_filename: Original uploaded filename

        Returns:
            Created sales_call row
        """
        org_id = self._ensure_org(user_id)

        result = (
            self.client.table("sales_calls")
            .insert({
                "org_id": org_id,
                "rep_id": user_id,
                "call_id": call_id,
                "audio_filename": audio_filename,
                "status": "pending",
            })
            .execute()
        )

        if not result.data:
            raise Exception("Failed to create sales call")

        return result.data[0]

    def update_sales_call_status(
        self,
        call_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> Dict:
        """
        Update the status of a sales_calls row.

        Sets completed_at when status is "completed".

        Args:
            call_id: Unique call identifier
            status: New status (pending/processing/transcribed/
                    completed/failed)
            error: Optional error message for failed status

        Returns:
            Updated sales_call row
        """
        data: Dict = {"status": status}
        if error:
            data["error"] = error
        if status == "completed":
            data["completed_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

        result = (
            self.client.table("sales_calls")
            .update(data)
            .eq("call_id", call_id)
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to update status for call {call_id}"
            )

        return result.data[0]

    def save_call_analysis(
        self,
        call_id: str,
        speaker_map: Dict,
        analysis: Dict,
        full_transcript: List[Dict],
    ) -> Dict:
        """
        Insert a call_analyses row from the analyzer output.

        Splits the flat analysis dict into the DB column layout:
        - Direct score columns (overall_rep_score, lead_score, etc.)
        - rep_analysis JSONB (strengths, improvements,
          coaching_tips, key_moments)
        - customer_analysis JSONB (customer_interests,
          objections_raised, buying_signals, suggested_next_steps)

        Args:
            call_id: Unique call identifier
            speaker_map: Output of identify_speakers()
            analysis: Output of analyze_call()
            full_transcript: Output of extract_speaker_turns()

        Returns:
            Created call_analyses row
        """
        call_row = (
            self.client.table("sales_calls")
            .select("org_id")
            .eq("call_id", call_id)
            .execute()
        )
        if not call_row.data:
            raise Exception(
                f"sales_calls row not found for call {call_id}"
            )
        org_id = call_row.data[0]["org_id"]

        rep_analysis = {
            "strengths": analysis.get("strengths", []),
            "improvements": analysis.get("improvements", []),
            "coaching_tips": analysis.get("coaching_tips", []),
            "key_moments": analysis.get("key_moments", []),
        }
        customer_analysis = {
            "customer_interests": analysis.get(
                "customer_interests", []
            ),
            "objections_raised": analysis.get(
                "objections_raised", []
            ),
            "buying_signals": analysis.get("buying_signals", []),
            "suggested_next_steps": analysis.get(
                "suggested_next_steps", []
            ),
        }

        data = {
            "call_id": call_id,
            "org_id": org_id,
            "salesperson_speaker_label": speaker_map.get(
                "salesperson_label"
            ),
            "customer_speaker_labels": speaker_map.get(
                "customer_labels", []
            ),
            "overall_rep_score": analysis.get("overall_rep_score"),
            "communication_score": analysis.get(
                "communication_score"
            ),
            "objection_handling_score": analysis.get(
                "objection_handling_score"
            ),
            "closing_score": analysis.get("closing_score"),
            "rep_analysis": json.dumps(rep_analysis),
            "lead_score": analysis.get("lead_score"),
            "engagement_level": analysis.get("engagement_level"),
            "customer_sentiment": analysis.get("customer_sentiment"),
            "customer_analysis": json.dumps(customer_analysis),
            "full_transcript": json.dumps(full_transcript),
        }

        result = (
            self.client.table("call_analyses").insert(data).execute()
        )

        if not result.data:
            raise Exception("Failed to save call analysis")

        return result.data[0]

    def get_call_analysis(self, call_id: str) -> Optional[Dict]:
        """
        Fetch a call's status and analysis, merged into one dict.

        Queries sales_calls for status + call_analyses for results.
        Returns None if the call does not exist.

        Args:
            call_id: Unique call identifier

        Returns:
            Merged dict or None
        """
        call_result = (
            self.client.table("sales_calls")
            .select(
                "call_id, status, error, audio_filename, created_at"
            )
            .eq("call_id", call_id)
            .execute()
        )

        if not call_result.data:
            return None

        row = call_result.data[0]

        analysis_result = (
            self.client.table("call_analyses")
            .select("*")
            .eq("call_id", call_id)
            .execute()
        )

        if analysis_result.data:
            row.update(analysis_result.data[0])

        return row

    def list_sales_calls(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        List sales calls for a user, newest first.

        Args:
            user_id: UUID of the user
            limit: Max rows to return (default 50)
            offset: Pagination offset (default 0)

        Returns:
            List of sales_calls rows
        """
        result = (
            self.client.table("sales_calls")
            .select(
                "*, call_analyses(overall_rep_score, lead_score,"
                " engagement_level, customer_sentiment)"
            )
            .eq("rep_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        rows = []
        for row in (result.data or []):
            analyses = row.pop("call_analyses", None) or []
            if analyses:
                row.update(analyses[0])
            rows.append(row)
        return rows

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _get_org_id(self, user_id: str) -> Optional[str]:
        """
        Look up the org_id for a user. Pure read — no side effects.

        Args:
            user_id: User UUID

        Returns:
            org_id string or None if the user has no org
        """
        result = (
            self.client.table("user_profiles")
            .select("org_id")
            .eq("id", user_id)
            .execute()
        )

        if result.data and result.data[0].get("org_id"):
            return result.data[0]["org_id"]
        return None

    def _ensure_org(self, user_id: str) -> str:
        """
        Return the org_id for a user, creating one if needed.

        Call only from write operations (POST/PUT). Never call
        from read operations — use _get_org_id instead.

        Args:
            user_id: User UUID from JWT

        Returns:
            org_id (UUID string)
        """
        org_id = self._get_org_id(user_id)
        if org_id:
            return org_id

        org_result = (
            self.client.table("organizations")
            .insert({"name": "My Organization"})
            .execute()
        )
        if not org_result.data:
            raise Exception("Failed to create organization")

        org_id = org_result.data[0]["id"]

        self.client.table("user_profiles").upsert({
            "id": user_id,
            "org_id": org_id,
            "role": "manager",
        }).execute()

        return org_id
