-- Migration 005: Billing subscriptions, org invites, and role expansion

-- Expand the role constraint to include 'owner' (account holder,
-- billing + team management, no calls) alongside existing roles.
-- Existing 'manager' rows are unchanged — they map to the player-coach role.
ALTER TABLE user_profiles
  DROP CONSTRAINT IF EXISTS user_profiles_role_check;
ALTER TABLE user_profiles
  ADD CONSTRAINT user_profiles_role_check
  CHECK (role IN ('owner', 'manager', 'rep'));

-- ---------------------------------------------------------------------------

CREATE TABLE subscriptions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID NOT NULL REFERENCES organizations(id),
    dodo_customer_id     TEXT,
    dodo_subscription_id TEXT,
    plan                 TEXT NOT NULL DEFAULT 'free',
    seat_limit           INTEGER NOT NULL DEFAULT 1,
    status               TEXT NOT NULL DEFAULT 'active',
    current_period_end   TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE subscriptions IS
  'One row per org tracking their Dodo Payments subscription state.';
COMMENT ON COLUMN subscriptions.dodo_customer_id IS
  'Dodo customer ID — required to open the billing portal.';
COMMENT ON COLUMN subscriptions.dodo_subscription_id IS
  'Dodo subscription ID — used to match incoming webhook events to this org.';
COMMENT ON COLUMN subscriptions.plan IS
  'Active plan name: free | solo | team | unlimited.';
COMMENT ON COLUMN subscriptions.seat_limit IS
  'Max user_profiles rows allowed for this org (1=solo, 5=team, 9999=unlimited).';
COMMENT ON COLUMN subscriptions.status IS
  'Mirrors Dodo subscription status: active | cancelled | failed | expired.';
COMMENT ON COLUMN subscriptions.current_period_end IS
  'Timestamp when the current billing period ends; NULL for free plan.';

CREATE UNIQUE INDEX ON subscriptions(org_id);
CREATE UNIQUE INDEX ON subscriptions(dodo_subscription_id)
  WHERE dodo_subscription_id IS NOT NULL;

-- ---------------------------------------------------------------------------

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

COMMENT ON TABLE org_invites IS
  'Invite tokens that managers share with reps to join their org.';
COMMENT ON COLUMN org_invites.token IS
  'URL-safe hex token embedded in the /join/:token invite link.';
COMMENT ON COLUMN org_invites.role IS
  'Role to assign to the invited user on acceptance: rep | manager.';
COMMENT ON COLUMN org_invites.expires_at IS
  'Invite expires 7 days after creation; NULL = no expiry.';
COMMENT ON COLUMN org_invites.accepted_at IS
  'Set when the invited user accepts. NULL = pending invite.';

CREATE INDEX ON org_invites(token);
CREATE INDEX ON org_invites(org_id);
