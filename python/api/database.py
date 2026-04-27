"""
Database service for Supabase PostgreSQL operations.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class DatabaseService:
    """Generic CRUD access to Supabase tables."""

    def __init__(self):
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

    def get_rows(
        self,
        *,
        table: str,
        filters: Optional[Dict] = None,
        select: str = "*",
        order_by: Optional[str] = None,
        ascending: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict]:
        """
        Fetch rows from `table`.

        filters: {col: scalar} equality, {col: list} for IN,
                 {col: None} for IS NULL.
        select: PostgREST select string — supports nested tables,
                e.g. "*, call_analyses(full_transcript)".
        """
        query = self.client.table(table).select(select)
        for col, val in (filters or {}).items():
            if val is None:
                query = query.is_(col, "null")
            elif isinstance(val, list):
                query = query.in_(col, val)
            else:
                query = query.eq(col, val)
        if order_by:
            query = query.order(order_by, desc=not ascending)
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.execute().data or []

    def add_row(self, *, table: str, data: Dict) -> Dict:
        """Insert a single row and return it."""
        result = self.client.table(table).insert(data).execute()
        if not result.data:
            raise Exception(f"Failed to insert row into {table}")
        return result.data[0]

    def upsert_row(self, *, table: str, data: Dict) -> Dict:
        """
        Insert or update a row on primary-key conflict.
        Only columns present in `data` are modified on conflict.
        """
        result = self.client.table(table).upsert(data).execute()
        if not result.data:
            raise Exception(f"Failed to upsert row in {table}")
        return result.data[0]

    def update_rows(
        self,
        *,
        table: str,
        data: Dict,
        filters: Dict,
    ) -> List[Dict]:
        """Update rows matching `filters` and return updated rows."""
        query = self.client.table(table).update(data)
        for col, val in filters.items():
            if val is None:
                query = query.is_(col, "null")
            elif isinstance(val, list):
                query = query.in_(col, val)
            else:
                query = query.eq(col, val)
        return query.execute().data or []

    def delete_rows(self, *, table: str, filters: Dict) -> None:
        """Delete rows matching `filters`."""
        query = self.client.table(table).delete()
        for col, val in filters.items():
            if val is None:
                query = query.is_(col, "null")
            elif isinstance(val, list):
                query = query.in_(col, val)
            else:
                query = query.eq(col, val)
        query.execute()


# ---------------------------------------------------------------------------
# Sales Analyzer database methods
# ---------------------------------------------------------------------------

class SalesDatabaseService(DatabaseService):
    """
    Extends DatabaseService with helpers that require business logic
    not expressible as a single CRUD call.
    """

    def ensure_org(self, user_id: str) -> str:
        """
        Return org_id for a user, creating an org if needed.
        Call before any write that requires an org_id.
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
        # Defaults to manager so new users can upload calls and access billing.
        # owner vs manager distinction to be revisited — see issue #5.
        self.client.table("user_profiles").upsert({
            "id": user_id,
            "org_id": org_id,
            "role": "manager",
        }).execute()
        self.client.table("subscriptions").insert({
            "org_id": org_id,
        }).execute()
        return org_id

    def list_products(
        self,
        user_id: str,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[Dict]:
        """
        List products visible to a user (org-scoped).
        Returns [] if the user has no org.

        # TODO (post-MVP): filter by team membership once teams table
        # is introduced.
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
            query = query.or_(self._build_or_filter(
                search,
                ["name", "description",
                 "customer_profile", "talking_points"],
            ))
        query = query.order(order_by, desc=order_desc)
        return query.execute().data or []

    def get_user_email(self, user_id: str) -> Optional[str]:
        """
        Fetch the email for a user via the Supabase admin API.
        Used in OAuth callbacks where no JWT is present.
        """
        try:
            resp = self.client.auth.admin.get_user_by_id(user_id)
            return resp.user.email if resp.user else None
        except Exception:
            return None

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _get_org_id(self, user_id: str) -> Optional[str]:
        rows = self.get_rows(
            table="user_profiles",
            filters={"id": user_id},
            select="org_id",
        )
        if rows and rows[0].get("org_id"):
            return rows[0]["org_id"]
        return None

    def _build_or_filter(
        self, search: str, columns: List[str]
    ) -> str:
        q = f"%{search}%"
        return ",".join(f"{col}.ilike.{q}" for col in columns)
