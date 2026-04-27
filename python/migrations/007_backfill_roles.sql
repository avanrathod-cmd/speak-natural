-- Migration 007: Backfill roles and seed missing subscription rows.

-- 1. Promote any 'rep' who signed up before the auth/init fix to 'manager'
--    so they retain full call upload + billing access.
UPDATE user_profiles SET role = 'manager' WHERE role = 'rep';

-- 2. Seed a free-tier subscriptions row for every org that predates the
--    billing feature (ensure_org now does this automatically for new orgs).
INSERT INTO subscriptions (org_id)
SELECT id FROM organizations
WHERE id NOT IN (SELECT org_id FROM subscriptions);
