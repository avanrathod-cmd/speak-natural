"""Billing API endpoints.

Routes (mounted at /billing in main.py):
    POST /checkout   — create Dodo checkout session
    POST /webhook    — handle Dodo webhook events (no auth)
    GET  /status     — current plan, seat usage, and user role
    GET  /portal     — Dodo billing portal URL (owner/manager only)

Roles with billing access: owner, manager.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from standardwebhooks import WebhookVerificationError

from api.auth import get_current_user
from dodopayments.types.subscription import Subscription
from api.database import SalesDatabaseService
from api.models import (
    AnalysisQuota,
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

    profile = _get_profile(user_id)
    org_id = profile.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")

    try:
        plan_id = billing_client.get_dodo_plan_id(req.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        checkout_url = billing_client.create_checkout_session(
            plan_id=plan_id,
            return_url=f"{_FRONTEND_URL}/billing?upgraded=true",
            org_id=org_id,
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
        billing_client.parse_webhook_event(
            payload=payload,
            webhook_id=request.headers.get("webhook-id", ""),
            webhook_timestamp=request.headers.get("webhook-timestamp", ""),
            webhook_signature=request.headers.get("webhook-signature", ""),
        )
    except WebhookVerificationError:
        raise HTTPException(
            status_code=401, detail="Invalid webhook signature"
        )

    body = json.loads(payload)
    _handle_subscription_event(
        event_type=body.get("type"),
        data=body.get("data"),
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
            analysis_quota=_build_analysis_quota(plan="free", used=0),
        )

    sub = _get_subscription(org_id)
    org = _get_org_usage(org_id)
    seats_used = org.get("seats_used", 0)
    minutes_analysed = org.get("minutes_analysed", 0)

    plan = sub.get("plan", "free") if sub else "free"
    analysis_quota = _build_analysis_quota(
        plan=plan, used=minutes_analysed
    )

    if sub:
        period_end = sub.get("current_period_end")
        return BillingStatusResponse(
            plan=plan,
            status=sub.get("status", "active"),
            role=role,
            seat_limit=sub.get("seat_limit", 1),
            seats_used=seats_used,
            period_end=str(period_end) if period_end else None,
            analysis_quota=analysis_quota,
        )

    return BillingStatusResponse(
        plan="free", status="active", role=role,
        seat_limit=1, seats_used=seats_used, period_end=None,
        analysis_quota=analysis_quota,
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


def _get_org_usage(org_id: str) -> dict:
    rows = _db.get_rows(
        table="organizations",
        filters={"id": org_id},
        select="seats_used, minutes_analysed",
    )
    return rows[0] if rows else {}


def _build_analysis_quota(
    plan: str, used: int
) -> Optional[AnalysisQuota]:
    limit = billing_client.get_analysis_minutes_limit(plan)
    if limit is None:
        return None
    return AnalysisQuota(
        quota_minutes=limit,
        used_minutes=used,
        remaining_minutes=max(0, limit - used),
    )


def _handle_subscription_event(
    event_type: Optional[str], data: Optional[dict]
) -> None:
    if not event_type or not event_type.startswith("subscription."):
        return
    if not data:
        return

    sub = Subscription.model_validate(data)
    subscription_id = sub.subscription_id
    customer_id = sub.customer.customer_id
    now = datetime.now(timezone.utc).isoformat()

    if event_type == "subscription.active":
        org_id = sub.metadata.get("org_id")
        if not org_id:
            logger.error(
                "subscription.active missing org_id in metadata "
                "(sub=%s) — cannot link to org", subscription_id,
            )
            return
        plan = billing_client.get_plan_name(sub.product_id)
        _update_subscription(
            filters={"org_id": org_id},
            update={
                "dodo_customer_id": customer_id,
                "dodo_subscription_id": subscription_id,
                "plan": plan,
                "seat_limit": billing_client.get_seat_limit(plan),
                "status": "active",
                "current_period_end": sub.next_billing_date.isoformat(),
                "updated_at": now,
            },
        )

    elif event_type == "subscription.renewed":
        _update_subscription(
            filters={"dodo_subscription_id": subscription_id},
            update={
                "current_period_end": sub.next_billing_date.isoformat(),
                "updated_at": now,
            },
        )

    elif event_type == "subscription.plan_changed":
        plan = billing_client.get_plan_name(sub.product_id)
        _update_subscription(
            filters={"dodo_subscription_id": subscription_id},
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
        _update_subscription(
            filters={"dodo_subscription_id": subscription_id},
            update={
                "plan": "free",
                "seat_limit": 1,
                "status": event_type.split(".")[1],
                "updated_at": now,
            },
        )


def _update_subscription(*, filters: dict, update: dict) -> None:
    if not _db.get_rows(table="subscriptions", filters=filters):
        logger.error(
            "No subscription row found for %s", filters
        )
        return
    _db.update_rows(table="subscriptions", data=update, filters=filters)
