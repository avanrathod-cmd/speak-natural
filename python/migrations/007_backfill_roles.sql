-- Migration 007: Backfill existing rep profiles to manager.
-- Users who signed up before the auth/init fix had no profile row created
-- at login, causing their role to default to 'rep'. Promote them to
-- 'manager' so they retain full call upload + billing access.

UPDATE user_profiles SET role = 'manager' WHERE role = 'rep';
