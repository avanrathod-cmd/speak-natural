# Billing + Team Management Plan

## Context

Item 4 of the Go-Live Plan. The goal is to charge for SpeakNatural
via Dodo Payments and enforce seat limits through a manager/rep
hierarchy. Currently every user gets their own solo org (`ensure_org`
auto-creates one). This plan adds:
- Three subscription tiers with seat limits
- Manager-initiated invite flow (copy-link, no email sending needed)
- Seat enforcement on invites and upgrades

---

## Pricing Tiers

| Plan | Price | Seats | Dodo Product |
|------|-------|-------|--------------|
| Free | $0 | 1 (manager only) | — |
| Solo | $39/month | 1 | DODO_SOLO_PRODUCT_ID |
| Team | $199/month | 5 | DODO_TEAM_PRODUCT_ID |
| Unlimited | $499/month | Unlimited | DODO_UNLIMITED_PRODUCT_ID |

Free plan = solo manager, no reps. Upgrade required to invite reps.

---

## Architecture Decisions

- **No separate memberships table.** Keep `user_profiles.org_id` +
  `user_profiles.role`. Invite acceptance sets `org_id` on the
  invited user's profile row. Minimal schema change.
- **Copy-link invites.** No email sending. Manager gets a link to
  share manually (same pattern as Slack guest links).
- **Seat count** = count of `user_profiles` rows with `org_id = X`.

---

## Step 1 — DB Migration `005_billing.sql`

Two new tables:

```sql
-- Subscription per org
CREATE TABLE subscriptions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL REFERENCES organizations(id),
    dodo_customer_id   TEXT,
    dodo_subscription_id TEXT,
    plan               TEXT NOT NULL DEFAULT 'free',
    seat_limit         INTEGER NOT NULL DEFAULT 1,
    status             TEXT NOT NULL DEFAULT 'active',
    current_period_end TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ON subscriptions(org_id);
CREATE UNIQUE INDEX ON subscriptions(dodo_subscription_id)
  WHERE dodo_subscription_id IS NOT NULL;

-- Invite tokens
CREATE TABLE org_invites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id),
    email       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'rep',
    token       TEXT NOT NULL UNIQUE
                  DEFAULT encode(gen_random_bytes(24), 'hex'),
    created_by  UUID NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ DEFAULT now() + INTERVAL '7 days',
    accepted_at TIMESTAMPTZ
);
CREATE INDEX ON org_invites(token);
CREATE INDEX ON org_invites(org_id);
```

Run on Supabase SQL editor after implementation.

---

## Step 2 — New environment variables

```
DODO_API_KEY=...
DODO_WEBHOOK_KEY=...
DODO_SOLO_PRODUCT_ID=...
DODO_TEAM_PRODUCT_ID=...
DODO_UNLIMITED_PRODUCT_ID=...
FRONTEND_URL=https://your-app.com
```

Add to Railway and `.env.example`.

---

## Step 3 — `python/utils/billing_client.py` (new)

Direct Dodo Payments API calls. No abstraction layer.

```python
def create_checkout_session(
    *, product_id, user_id, customer_email,
    customer_name, success_url, cancel_url
) -> str:   # returns checkout_url

def create_portal_session(
    *, customer_id, return_url
) -> str:   # returns portal_url

def parse_webhook_event(
    *, payload: bytes, webhook_id: str,
    webhook_timestamp: str, webhook_signature: str
) -> dict:  # raises ValueError on bad signature
```

SDK: `client = dodopayments.Dodopayments(bearer_auth=DODO_API_KEY)`

Add `"dodopayments>=0.7.0"` to `pyproject.toml`.

---

## Step 4 — `python/api/billing_service.py` (new)

Mounted at `/billing` in `main.py`.

```
POST /billing/checkout
  Auth: required (manager only — 403 if role != 'manager')
  Body: {plan: "solo" | "team" | "unlimited"}
  → {checkout_url: str}
  Maps plan name → DODO_*_PRODUCT_ID env var.
  success_url = FRONTEND_URL + /billing?upgraded=true
  cancel_url  = FRONTEND_URL + /billing

POST /billing/webhook
  Auth: none — verified by Dodo signature headers
  (webhook-id, webhook-timestamp, webhook-signature)
  Events handled:
    subscription.active      → upsert subscriptions row,
                                set plan + seat_limit + status=active
    subscription.renewed     → update current_period_end
    subscription.plan_changed → update plan + seat_limit
    subscription.cancelled   → plan=free, seat_limit=1, status=cancelled
    subscription.failed      → plan=free, seat_limit=1, status=failed
  seat_limit: solo→1, team→5, unlimited→9999

GET /billing/status
  Auth: required
  → {plan, status, seat_limit, seats_used, period_end}
  seats_used = COUNT(user_profiles WHERE org_id = user's org)

GET /billing/portal
  Auth: required (manager only)
  → {portal_url: str}
  Fetches dodo_customer_id from subscriptions row, creates portal.
  Returns 400 if no paid subscription exists.
```

New Pydantic models in `models.py`:
- `CheckoutRequest(plan: str)`
- `CheckoutResponse(checkout_url: str)`
- `BillingStatusResponse(plan, status, seat_limit, seats_used, period_end)`
- `PortalResponse(portal_url: str)`

---

## Step 5 — `python/api/team_service.py` (new)

Mounted at `/team` in `main.py`.

```
POST /team/invite
  Auth: required (manager only)
  Body: {email: str, role: "rep"}
  Guards: seats_used < seat_limit → 402 if at limit
  Creates org_invites row.
  → {invite_url: str}  (FRONTEND_URL/join/<token>)

GET /team/members
  Auth: required
  → [{user_id, email, role, full_name, created_at}]
  All user_profiles WHERE org_id = user's org.
  Email fetched via Supabase admin API per member.

DELETE /team/members/{member_user_id}
  Auth: required (manager only, cannot remove self)
  Clears member's org_id → NULL, resets role → 'rep'.
  → 204

GET /team/invite/{token}    (public — no auth)
  Validates token (not expired, not accepted).
  → {org_name: str, invited_email: str, role: str}

POST /team/accept/{token}
  Auth: required
  Validates token. Sets user_profiles.org_id + role.
  Marks invite accepted_at = now().
  → {org_id: str}
```

New Pydantic models in `models.py`:
- `InviteRequest(email: str, role: str = "rep")`
- `InviteResponse(invite_url: str)`
- `InviteInfoResponse(org_name, invited_email, role)`
- `TeamMember(user_id, email, role, full_name, created_at)`

---

## Step 6 — `python/api/main.py` changes

```python
from api.billing_service import billing_router
from api.team_service import team_router
app.include_router(billing_router, prefix="/billing")
app.include_router(team_router, prefix="/team")
```

---

## Step 7 — Frontend: `PricingPage.tsx` (new)

Route: `/pricing` — **public** (no auth required)

Three plan cards (Free → Solo → Team → Unlimited).
- Not logged in: "Get Started" button → redirects to signup/login
- Logged in: current plan gets "Current Plan" badge; other plans
  show "Upgrade →" → calls `POST /billing/checkout` → redirects
  to `checkout_url`

Link to `/pricing` from the landing page when it gets built.

---

## Step 8 — Frontend: `BillingPage.tsx` (new)

Route: `/billing`

Sections:
1. Plan badge (Free / Solo / Team / Unlimited) + period end
2. "X of Y seats used" with simple progress bar
3. Team members list — name, email, role, [Remove] button
4. Invite input — email + "Get Invite Link" → copies link to clipboard
5. "Manage Billing" → `GET /billing/portal` → new tab
6. "View Plans" link → `/pricing`

On mount: if `?upgraded=true` in URL, show success banner and
clear the param with `window.history.replaceState`.

---

## Step 9 — Frontend: `JoinPage.tsx` (new)

Route: `/join/:token` — public (before auth guard in `App.tsx`)

- **Not logged in:** `GET /team/invite/:token` → show org name +
  invited email. "Create account / Sign in" button stores token in
  `localStorage('pending_invite_token')` then redirects to Supabase
  auth.
- **Logged in:** auto-`POST /team/accept/:token` on mount → redirect
  to `/dashboard`.

In `App.tsx` post-auth effect: check `localStorage` for
`pending_invite_token`; if present, call accept and clear it.

---

## Step 10 — `api.ts` additions (8 new methods)

```typescript
getBillingStatus(token): Promise<BillingStatus>
createCheckout(plan, token): Promise<{ checkout_url: string }>
getBillingPortal(token): Promise<{ portal_url: string }>
getTeamMembers(token): Promise<TeamMember[]>
inviteMember(email, token): Promise<{ invite_url: string }>
removeMember(userId, token): Promise<void>
getInviteInfo(inviteToken): Promise<InviteInfo>   // no auth
acceptInvite(inviteToken, token): Promise<void>
```

---

## Step 11 — `App.tsx` changes

```tsx
// Public routes:
<Route path="/join/:token" element={<JoinPage />} />

// Authenticated routes:
<Route path="/pricing" element={<PricingPage />} />
<Route path="/billing" element={<BillingPage />} />
```

Add post-auth invite check in the `useEffect` that watches `user`.
Add "Billing" link on `ProfilePage.tsx`.

---

## Step 12 — Manager dashboard: rep filtering

The existing `CallDashboard` is extended for managers. No new page.

### Backend

`GET /sales/calls` currently filters by `rep_id = user_id`. Change:
- If caller is a manager → return all calls for the org
- Add optional `?rep_id=<uuid>` query param to filter by a specific rep
- Each call item already has `rep_id`; add `rep_name` (from
  `user_profiles.full_name`) via a joined select

`GET /sales/reps` (new, manager only):
- Returns `[{user_id, full_name, email}]` for all reps in the org
- Used to populate the filter dropdown

Add `rep_name: Optional[str]` to `CallListItemResponse` in `models.py`.

### Frontend

`CallDashboard.tsx` changes (manager only, driven by `role` from auth):
- **Rep filter dropdown** above the call list: "All reps ▾" →
  select a specific rep to filter
- **Rep name column** in the call list rows (hidden for reps)
- Populate dropdown via `GET /sales/reps`
- Filter applies as a query param on `GET /sales/calls?rep_id=`

```
┌────────────────────────────────────────────────────────┐
│  All reps ▾    [Search calls…]            Sort: Latest │
├────────────────────────────────────────────────────────┤
│  Rahul Sharma   Discovery call    78/100   Apr 20      │
│  Priya Mehta    Demo — Acme Corp  82/100   Apr 19      │
│  Rahul Sharma   Follow-up         71/100   Apr 18      │
└────────────────────────────────────────────────────────┘
```

---

## Files Summary

| File | Action |
|------|--------|
| `python/migrations/005_billing.sql` | Create |
| `python/utils/billing_client.py` | Create |
| `python/api/billing_service.py` | Create |
| `python/api/team_service.py` | Create |
| `python/api/models.py` | Add 8 billing/team models + rep_name field |
| `python/api/main.py` | Add 2 routers |
| `python/api/sales_service.py` | Extend GET /calls for manager scope + GET /reps |
| `python/pyproject.toml` | Add dodopayments dep |
| `ui/wireframe/src/pages/PricingPage.tsx` | Create |
| `ui/wireframe/src/pages/BillingPage.tsx` | Create |
| `ui/wireframe/src/pages/JoinPage.tsx` | Create |
| `ui/wireframe/src/services/api.ts` | Add 8 billing/team methods + getReps |
| `ui/wireframe/src/App.tsx` | Add 3 routes + invite check |
| `ui/wireframe/src/pages/ProfilePage.tsx` | Add Billing link |
| `ui/wireframe/src/components/CallDashboard.tsx` | Add rep filter + rep name column |

---

## Test Checklist

1. Create 3 products in Dodo test dashboard, copy product IDs.
2. Set all 6 env vars locally.
3. Run `uv sync` (picks up dodopayments).
4. Apply migration 005 on Supabase SQL editor.
5. `GET /billing/status` → `{plan:"free", seat_limit:1, seats_used:1}`
6. `/pricing` → click Solo → Dodo Checkout → complete with test card.
7. Dodo fires `subscription.active` → subscriptions row plan=solo.
8. `/billing` shows Solo badge, "1 of 1 seats used", no Invite shown.
9. Upgrade to Team → seat_limit=5 → Invite button appears.
10. Invite rep → copy link → rep opens `/join/:token`.
11. Rep signs up → auto-accepts → appears in team member list.
12. Manager removes rep → rep can no longer see org data.
13. `GET /billing/portal` → Dodo portal opens in new tab.
