"""Dodo Payments API wrapper."""

import logging
import os

from dodopayments import DodoPayments

logger = logging.getLogger(__name__)

# Dodo plan IDs (set these in environment variables via the Dodo dashboard).
# Named "plan" to avoid confusion with the app's own sales `products` table.
_DODO_PLAN_IDS: dict[str, str] = {
    "solo":      os.getenv("DODO_SOLO_PLAN_ID", ""),
    "team":      os.getenv("DODO_TEAM_PLAN_ID", ""),
    "unlimited": os.getenv("DODO_UNLIMITED_PLAN_ID", ""),
}

_PLAN_SEAT_LIMITS: dict[str, int] = {
    "free":      1,
    "solo":      1,
    "team":      5,
    "unlimited": 9999,
}


def _client() -> DodoPayments:
    return DodoPayments(
        bearer_token=os.environ["DODO_API_KEY"],
        environment=os.getenv("DODO_ENVIRONMENT", "test_mode"),
        webhook_key=os.getenv("DODO_WEBHOOK_KEY", ""),
    )


def get_dodo_plan_id(plan: str) -> str:
    pid = _DODO_PLAN_IDS.get(plan)
    if not pid:
        raise ValueError(f"No Dodo plan ID configured for: {plan}")
    return pid


def get_seat_limit(plan: str) -> int:
    return _PLAN_SEAT_LIMITS.get(plan, 1)


def create_checkout_session(
    *,
    plan_id: str,
    customer_email: str,
    customer_name: str,
    return_url: str,
) -> str:
    """Return Dodo hosted checkout URL for the given plan."""
    session = _client().checkout_sessions.create(
        product_cart=[{"product_id": plan_id, "quantity": 1}],
        customer={"email": customer_email, "name": customer_name},
        return_url=return_url,
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
    return session.url


def parse_webhook_event(
    *,
    payload: bytes,
    webhook_id: str,
    webhook_timestamp: str,
    webhook_signature: str,
):
    """Verify Dodo webhook signature and return the event object.

    Raises ValueError on invalid signature.
    """
    try:
        return _client().webhooks.unwrap(
            payload,
            headers={
                "webhook-id": webhook_id,
                "webhook-signature": webhook_signature,
                "webhook-timestamp": webhook_timestamp,
            },
        )
    except Exception as exc:
        raise ValueError(f"Webhook verification failed: {exc}") from exc
