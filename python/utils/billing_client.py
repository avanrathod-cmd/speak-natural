"""Dodo Payments API wrapper."""

import logging
import os
from dataclasses import dataclass

from dodopayments import DodoPayments

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanLimits:
    seat_limit: int
    analysis_minutes: int | None  # None = unlimited
    dodo_plan_id: str             # empty string for free (no Dodo product)


_PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        seat_limit=1,
        analysis_minutes=240,
        dodo_plan_id="",
    ),
    "solo": PlanLimits(
        seat_limit=1,
        analysis_minutes=None,
        dodo_plan_id=os.getenv("DODO_SOLO_PLAN_ID", ""),
    ),
    "team": PlanLimits(
        seat_limit=5,
        analysis_minutes=None,
        dodo_plan_id=os.getenv("DODO_TEAM_PLAN_ID", ""),
    ),
    "unlimited": PlanLimits(
        seat_limit=9999,
        analysis_minutes=None,
        dodo_plan_id=os.getenv("DODO_UNLIMITED_PLAN_ID", ""),
    ),
}


def _client() -> DodoPayments:
    return DodoPayments(
        bearer_token=os.environ["DODO_API_KEY"],
        environment=os.getenv("DODO_ENVIRONMENT", "test_mode"),
        webhook_key=os.getenv("DODO_WEBHOOK_KEY", ""),
    )


class QuotaExceededError(Exception):
    """Raised when an org's analysis quota would be exceeded."""


def get_dodo_plan_id(plan: str) -> str:
    limits = _PLANS.get(plan)
    if not limits or not limits.dodo_plan_id:
        raise ValueError(f"No Dodo plan ID configured for: {plan}")
    return limits.dodo_plan_id


def get_plan_name(product_id: str) -> str:
    """Reverse-lookup Dodo product ID → plan name."""
    for name, limits in _PLANS.items():
        if limits.dodo_plan_id and limits.dodo_plan_id == product_id:
            return name
    return "solo"


def get_seat_limit(plan: str) -> int:
    return _PLANS.get(plan, _PLANS["free"]).seat_limit


def get_analysis_minutes_limit(plan: str) -> int | None:
    """Returns quota in minutes, or None if unlimited."""
    return _PLANS.get(plan, _PLANS["free"]).analysis_minutes


def check_analysis_quota(
    plan: str, used_minutes: int, incoming_minutes: int
) -> None:
    """Raises QuotaExceededError if quota would be exceeded."""
    limit = get_analysis_minutes_limit(plan)
    if limit is not None and used_minutes + incoming_minutes > limit:
        raise QuotaExceededError(
            f"Free plan limit reached. You have used {used_minutes} of"
            f" your {limit}-minute analysis quota. Upgrade to continue."
        )


def create_checkout_session(
    *, plan_id: str, return_url: str, org_id: str
) -> str:
    """Return Dodo hosted checkout URL for the given plan."""
    session = _client().checkout_sessions.create(
        product_cart=[{"product_id": plan_id, "quantity": 1}],
        return_url=return_url,
        metadata={"org_id": org_id},
    )
    return session.checkout_url


def create_portal_session(
    *,
    customer_id: str,
    return_url: str,
) -> str:
    """Return Dodo billing portal URL for an existing customer."""
    session = _client().customers.customer_portal.create(
        customer_id,
        return_url=return_url,
    )
    return session.link


def parse_webhook_event(
    *,
    payload: bytes,
    webhook_id: str,
    webhook_timestamp: str,
    webhook_signature: str,
):
    """Verify Dodo webhook signature and return the event object.

    Raises WebhookVerificationError on invalid signature.
    All other exceptions propagate as-is.
    """
    return _client().webhooks.unwrap(
        payload.decode("utf-8"),
        headers={
            "webhook-id": webhook_id,
            "webhook-signature": webhook_signature,
            "webhook-timestamp": webhook_timestamp,
        },
    )
