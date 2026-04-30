"""Team management API endpoints.

Routes (mounted at /team in main.py):
    POST   /invite              — owner/manager generates an invite link
    GET    /members             — list org members
    DELETE /members/{user_id}   — remove a member from the org
    GET    /invite/{token}      — get invite info (public, no auth)
    POST   /accept/{token}      — accept an invite (auth required)

Roles:
    owner   — billing + team management, does not record calls, free seat
    manager — team management + records calls, counts as a seat
    rep     — records calls only, counts as a seat
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import get_current_user
from api.database import SalesDatabaseService
from api.models import (
    InviteInfoResponse,
    InviteRequest,
    InviteResponse,
    OrgResponse,
    OrgUpdateRequest,
    RepSummary,
    TeamMember,
)

logger = logging.getLogger(__name__)

team_router = APIRouter(tags=["Team"])
_db = SalesDatabaseService()

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Roles that can manage the team
_TEAM_ADMIN_ROLES = {"owner", "manager"}

# Roles that consume a paid seat (they record/analyze calls)
_SEAT_ROLES = {"manager", "rep"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@team_router.get("/org", response_model=OrgResponse)
async def get_org(user: dict = Depends(get_current_user)):
    profile = _require_team_admin(user["user_id"])
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")
    rows = _db.get_rows(
        table="organizations",
        filters={"id": org_id},
        select="name",
    )
    name = rows[0]["name"] if rows else "My Organization"
    return OrgResponse(org_id=org_id, name=name)


@team_router.patch("/org", response_model=OrgResponse)
async def update_org(
    req: OrgUpdateRequest,
    user: dict = Depends(get_current_user),
):
    profile = _require_team_admin(user["user_id"])
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")
    _db.update_rows(
        table="organizations",
        data={"name": req.name},
        filters={"id": org_id},
    )
    return OrgResponse(org_id=org_id, name=req.name)


@team_router.get("/reps", response_model=list[RepSummary])
async def list_reps(user: dict = Depends(get_current_user)):
    """List reps and managers in the org. Owner/manager only.

    Used by the frontend to populate the rep filter dropdown on the
    dashboard.
    """
    profile = _require_team_admin(user["user_id"])
    org_id = profile.get("org_id")
    if not org_id:
        return []

    rows = _db.get_rows(
        table="user_profiles",
        filters={"org_id": org_id, "role": ["manager", "rep"]},
        select="id, full_name",
    )
    return [
        RepSummary(
            user_id=row["id"],
            email=_db.get_user_email(row["id"]),
            full_name=row.get("full_name"),
        )
        for row in rows
    ]


@team_router.post("/invite", response_model=InviteResponse)
async def invite_member(
    req: InviteRequest,
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]
    profile = _require_team_admin(user_id)
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")

    if req.role in _SEAT_ROLES:
        seats_used = _get_seats_used(org_id)
        seat_limit = _get_seat_limit(org_id)
        if seats_used >= seat_limit:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Seat limit reached ({seats_used}/{seat_limit}). "
                    "Upgrade your plan to invite more members."
                ),
            )

    row = _db.add_row(
        table="org_invites",
        data={
            "org_id": org_id,
            "email": req.email,
            "role": req.role,
            "created_by": user_id,
        },
    )
    return InviteResponse(
        invite_url=f"{_FRONTEND_URL}/join/{row['token']}"
    )


@team_router.get("/members", response_model=list[TeamMember])
async def list_members(user: dict = Depends(get_current_user)):
    profile = _get_profile(user["user_id"])
    org_id = profile.get("org_id")
    if not org_id:
        return []

    rows = _db.get_rows(
        table="user_profiles",
        filters={"org_id": org_id},
        select="id, role, full_name, created_at",
    )
    return [
        TeamMember(
            user_id=row["id"],
            email=_db.get_user_email(row["id"]),
            role=row.get("role", "rep"),
            full_name=row.get("full_name"),
            created_at=(
                str(row["created_at"]) if row.get("created_at") else None
            ),
        )
        for row in rows
    ]


@team_router.delete("/members/{member_user_id}", status_code=204)
async def remove_member(
    member_user_id: str,
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]
    _require_team_admin(user_id)

    if member_user_id == user_id:
        raise HTTPException(
            status_code=400, detail="Cannot remove yourself"
        )

    profile = _get_profile(member_user_id)
    removed_role = profile.get("role")
    org_id = profile.get("org_id")

    _db.update_rows(
        table="user_profiles",
        data={"org_id": None, "role": "rep"},
        filters={"id": member_user_id},
    )

    if removed_role in _SEAT_ROLES and org_id:
        _decrement_seats_used(org_id)

    return Response(status_code=204)


@team_router.get("/invite/{token}", response_model=InviteInfoResponse)
async def get_invite_info(token: str):
    """Public — no auth required. Used to show org name before signup."""
    invite = _validate_invite_token(token)

    org_rows = _db.get_rows(
        table="organizations",
        filters={"id": invite["org_id"]},
        select="name",
    )
    org_name = org_rows[0]["name"] if org_rows else "Unknown Organization"

    return InviteInfoResponse(
        org_name=org_name,
        invited_email=invite["email"],
        role=invite["role"],
    )


@team_router.post("/accept/{token}")
async def accept_invite(
    token: str,
    user: dict = Depends(get_current_user),
):
    invite = _validate_invite_token(token)

    org_id = invite["org_id"]
    role = invite["role"]

    _db.update_rows(
        table="user_profiles",
        data={"org_id": org_id, "role": role},
        filters={"id": user["user_id"]},
    )
    _db.update_rows(
        table="org_invites",
        data={"accepted_at": datetime.now(timezone.utc).isoformat()},
        filters={"id": invite["id"]},
    )

    if role in _SEAT_ROLES:
        _increment_seats_used(org_id)

    return {"org_id": org_id}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_profile(user_id: str) -> dict:
    rows = _db.get_rows(
        table="user_profiles",
        filters={"id": user_id},
        select="org_id, role",
    )
    return rows[0] if rows else {}


def _require_team_admin(user_id: str) -> dict:
    profile = _get_profile(user_id)
    if profile.get("role") not in _TEAM_ADMIN_ROLES:
        raise HTTPException(
            status_code=403, detail="Owner or manager access required"
        )
    return profile


def _get_seats_used(org_id: str) -> int:
    rows = _db.get_rows(
        table="organizations",
        filters={"id": org_id},
        select="seats_used",
    )
    return rows[0]["seats_used"] if rows else 0


def _increment_seats_used(org_id: str) -> None:
    current = _get_seats_used(org_id)
    _db.update_rows(
        table="organizations",
        data={"seats_used": current + 1},
        filters={"id": org_id},
    )


def _decrement_seats_used(org_id: str) -> None:
    current = _get_seats_used(org_id)
    _db.update_rows(
        table="organizations",
        data={"seats_used": max(0, current - 1)},
        filters={"id": org_id},
    )


def _get_seat_limit(org_id: str) -> int:
    rows = _db.get_rows(
        table="subscriptions",
        filters={"org_id": org_id},
        select="seat_limit",
    )
    return rows[0]["seat_limit"] if rows else 1


def _validate_invite_token(token: str) -> dict:
    rows = _db.get_rows(
        table="org_invites",
        filters={"token": token},
        select="id, org_id, email, role, expires_at, accepted_at",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Invite not found")

    invite = rows[0]
    if invite.get("accepted_at"):
        raise HTTPException(
            status_code=410, detail="Invite already accepted"
        )

    expires_at = invite.get("expires_at")
    if expires_at:
        exp = datetime.fromisoformat(
            str(expires_at).replace("Z", "+00:00")
        )
        if exp < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=410, detail="Invite has expired"
            )

    return invite
