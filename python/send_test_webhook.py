"""
Send a signed subscription.active webhook to local FastAPI server.
Run from python/ directory: uv run python send_test_webhook.py
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
import urllib.request
import urllib.error
from dotenv import load_dotenv
import os

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_ORG  = "aee445f4-829b-42fa-b370-52bf5f8d7bec"
PLAN_ID     = os.getenv("DODO_SOLO_PLAN_ID", "pdt_0NdajqWZBRtmFpNxskQ7U")
WEBHOOK_KEY = os.getenv("DODO_WEBHOOK_KEY", "")
BASE_URL    = "http://localhost:8000"

# ── Build payload ─────────────────────────────────────────────────────────────

SUB_ID  = f"sub_test_{uuid.uuid4().hex[:8]}"
CUST_ID = f"cus_test_{uuid.uuid4().hex[:8]}"
NEXT_BILLING = "2026-05-27"

payload = {
    "type": "subscription.active",
    "data": {
        "subscription_id": SUB_ID,
        "customer": {
            "customer_id": CUST_ID,
            "email": "test@example.com",
            "name": "Test User",
        },
        "product_id": PLAN_ID,
        "status": "active",
        "next_billing_date": NEXT_BILLING,
        "previous_billing_date": "2026-03-27T00:00:00Z",
        "metadata": {"org_id": TARGET_ORG},
        "quantity": 1,
        "currency": "USD",
        "recurring_pre_tax_amount": 2900,
        "payment_frequency_count": 1,
        "payment_frequency_interval": "Month",
        "subscription_period_count": 1,
        "subscription_period_interval": "Month",
        "trial_period_days": 0,
        "tax_inclusive": False,
        "cancel_at_next_billing_date": False,
        "on_demand": False,
        "addons": [],
        "meters": [],
        "credit_entitlement_cart": [],
        "meter_credit_entitlement_cart": [],
        "billing": {"country": "US"},
        "created_at": "2026-04-27T00:00:00Z",
        "updated_at": "2026-04-27T00:00:00Z",
    },
}

body = json.dumps(payload).encode("utf-8")

# ── Sign (Standard Webhooks: HMAC-SHA256) ─────────────────────────────────────

# whsec_ prefix → strip, base64-decode to get raw key bytes
raw_key = base64.b64decode(WEBHOOK_KEY.removeprefix("whsec_"))

wh_id        = f"msg_{uuid.uuid4().hex}"
wh_timestamp = str(int(time.time()))

signed_content = f"{wh_id}.{wh_timestamp}.{body.decode()}".encode("utf-8")
sig_bytes = hmac.new(raw_key, signed_content, hashlib.sha256).digest()
sig_b64   = base64.b64encode(sig_bytes).decode()
wh_signature = f"v1,{sig_b64}"

headers = {
    "Content-Type": "application/json",
    "webhook-id":        wh_id,
    "webhook-timestamp": wh_timestamp,
    "webhook-signature": wh_signature,
}

# ── Send ──────────────────────────────────────────────────────────────────────

url = f"{BASE_URL}/billing/webhook"
print(f"POST {url}")
print(f"  webhook-id:        {wh_id}")
print(f"  webhook-timestamp: {wh_timestamp}")
print(f"  webhook-signature: {wh_signature}")
print(f"  payload type:      {payload['type']}")
print(f"  org_id:            {TARGET_ORG}")
print()

req = urllib.request.Request(url, data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        print(f"Status: {resp.status}")
        print(f"Body:   {resp.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except urllib.error.URLError as e:
    print(f"Connection error: {e.reason}")
    print("Is the server running? cd python && uv run uvicorn api.main:app --reload")
