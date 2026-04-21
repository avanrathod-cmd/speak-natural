"""Billing API endpoints.

Routes (mounted at /billing in main.py):
    POST /checkout   — create Dodo checkout session
    POST /webhook    — handle Dodo webhook events (no auth)
    GET  /status     — current plan, seat usage, and user role
    GET  /portal     — Dodo billing portal URL (owner/manager only)

Roles with billing access: owner, manager.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import get_current_user
from api.database import SalesDatabaseService
from api.models import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from utils import billing_client

logger = logging.getLogger(__name__)

billing_router = APIRouter(tags=["Billing"])
_db = SalesDatabaseService()

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
_BILLING_ROLES = {"owner", "manager"}
_SEAT_ROLES = {"manager", "rep"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@billing_router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    req: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]
    _require_billing_access(user_id)

    try:
        plan_id = billing_client.get_dodo_plan_id(req.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    email = _db.get_user_email(user_id) or user.get("email", "")
    try:
        checkout_url = billing_client.create_checkout_session(
            plan_id=plan_id,
            customer_email=email,
            customer_name=email.split("@")[0],
            return_url=f"{_FRONTEND_URL}/billing?upgraded=true",
        )
    except Exception as exc:
        logger.error("Checkout creation failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to create checkout session"
        )

    return CheckoutResponse(checkout_url=checkout_url)


@billing_router.post("/webhook")
async def billing_webhook(request: Request):
    payload = await request.body()

    try:
        event = billing_client.parse_webhook_event(
            payload=payload,
            webhook_id=request.headers.get("webhook-id", ""),
            webhook_timestamp=request.headers.get("webhook-timestamp", ""),
            webhook_signature=request.headers.get("webhook-signature", ""),
        )
    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid webhook signature"
        )

    _handle_subscription_event(
        event_type=_extract(event, "type"),
        data=_extract(event, "data") or {},
    )
    return {"received": True}


@billing_router.get("/status", response_model=BillingStatusResponse)
async def billing_status(user: dict = Depends(get_current_user)):
    profile = _get_profile(user["user_id"])
    org_id = profile.get("org_id")
    role = profile.get("role", "rep")

    if not org_id:
        return BillingStatusResponse(
            plan="free", status="active", role=role,
            seat_limit=1, seats_used=0, period_end=None,
        )

    sub = _get_subscription(org_id)
    seats_used = _count_seats(org_id)

    if sub:
        period_end = sub.get("current_period_end")
        return BillingStatusResponse(
            plan=sub.get("plan", "free"),
            status=sub.get("status", "active"),
            role=role,
            seat_limit=sub.get("seat_limit", 1),
            seats_used=seats_used,
            period_end=str(period_end) if period_end else None,
        )

    return BillingStatusResponse(
        plan="free", status="active", role=role,
        seat_limit=1, seats_used=seats_used, period_end=None,
    )


@billing_router.get("/portal", response_model=PortalResponse)
async def billing_portal(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    _require_billing_access(user_id)

    profile = _get_profile(user_id)
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")

    sub = _get_subscription(org_id)
    if not sub or not sub.get("dodo_customer_id"):
        raise HTTPException(
            status_code=400, detail="No paid subscription found"
        )

    try:
        portal_url = billing_client.create_portal_session(
            customer_id=sub["dodo_customer_id"],
            return_url=f"{_FRONTEND_URL}/billing",
        )
    except Exception as exc:
        logger.error("Portal session creation failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to create portal session"
        )

    return PortalResponse(portal_url=portal_url)


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


def _require_billing_access(user_id: str) -> None:
    if _get_profile(user_id).get("role") not in _BILLING_ROLES:
        raise HTTPException(
            status_code=403, detail="Owner or manager access required"
        )


def _get_subscription(org_id: str) -> Optional[dict]:
    rows = _db.get_rows(
        table="subscriptions",
        filters={"org_id": org_id},
    )
    return rows[0] if rows else None


def _count_seats(org_id: str) -> int:
    """Count members who consume a paid seat (manager + rep, not owner)."""
    rows = _db.get_rows(
        table="user_profiles",
        filters={"org_id": org_id, "role": list(_SEAT_ROLES)},
        select="id",
    )
    return len(rows)


def _extract(data, field: str):
    """Read a field from a Pydantic model or a plain dict."""
    if hasattr(data, field):
        return getattr(data, field)
    if isinstance(data, dict):
        return data.get(field)
    return None


def _handle_subscription_event(
    event_type: Optional[str], data
) -> None:
    if not event_type or not event_type.startswith("subscription."):
        return

    customer_id = _extract(data, "customer_id")
    subscription_id = _extract(data, "subscription_id")

    if not customer_id and not subscription_id:
        logger.warning(
            "Webhook %s missing customer/subscription IDs", event_type
        )
        return

    now = datetime.now(timezone.utc).isoformat()

    if event_type == "subscription.active":
        plan = _extract(data, "plan") or "free"
        _upsert_subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            update={
                "dodo_customer_id": customer_id,
                "dodo_subscription_id": subscription_id,
                "plan": plan,
                "seat_limit": billing_client.get_seat_limit(plan),
                "status": "active",
                "current_period_end": _extract(
                    data, "current_period_end"
                ),
                "updated_at": now,
            },
        )

    elif event_type == "subscription.renewed":
        _upsert_subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            update={
                "current_period_end": _extract(
                    data, "current_period_end"
                ),
                "updated_at": now,
            },
        )

    elif event_type == "subscription.plan_changed":
        plan = _extract(data, "plan") or "free"
        _upsert_subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            update={
                "plan": plan,
                "seat_limit": billing_client.get_seat_limit(plan),
                "updated_at": now,
            },
        )

    elif event_type in (
        "subscription.cancelled",
        "subscription.failed",
        "subscription.expired",
    ):
        _upsert_subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            update={
                "plan": "free",
                "seat_limit": 1,
                "status": event_type.split(".")[1],
                "updated_at": now,
            },
        )


def _upsert_subscription(
    *,
    subscription_id: Optional[str],
    customer_id: Optional[str],
    update: dict,
) -> None:
    filters = None

    if subscription_id:
        rows = _db.get_rows(
            table="subscriptions",
            filters={"dodo_subscription_id": subscription_id},
        )
        if rows:
            filters = {"dodo_subscription_id": subscription_id}

    if not filters and customer_id:
        rows = _db.get_rows(
            table="subscriptions",
            filters={"dodo_customer_id": customer_id},
        )
        if rows:
            filters = {"dodo_customer_id": customer_id}

    if filters:
        _db.update_rows(
            table="subscriptions", data=update, filters=filters
        )
    else:
        logger.warning(
            "No subscription row found for sub=%s customer=%s",
            subscription_id,
            customer_id,
        )
