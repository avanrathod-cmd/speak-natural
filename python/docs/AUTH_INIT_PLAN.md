# Auth Init Plan

## Problem

Two issues triggered by the same root cause — user profiles are created lazily
(only when `ensure_org` is called on first upload/connect), not at signup:

1. **Wrong role on first load** — billing/profile endpoints default to `role: rep`
   when no `user_profiles` row exists yet.
2. **Generic org name** — org is always created as `"My Organization"` with no
   way to change it.

---

## Architecture Principle

The frontend should interact with the backend for all data operations.
Supabase on the frontend is used only for auth — the OAuth redirect dance
and JWT management. These are browser-native and cannot go through the backend.

```
Browser ←→ Supabase    (auth only — OAuth initiation + JWT management)
Browser ←→ Your API    (everything else, JWT attached as Bearer token)
```

## Current Flow

```
User clicks "Sign in with Google"
  → supabase.auth.signInWithOAuth() — browser redirect to Google
  → Google redirects back, Supabase issues JWT
  → onAuthStateChange fires in AuthContext.tsx
      → sets user state, nothing else  ← no backend call

First upload / Attendee connect
  → ensure_org(user_id) called lazily
      → creates org: "My Organization"
      → creates user_profiles row: role = owner  ← wrong, owners can't upload calls
  ✗ Any endpoint hit before this sees role = "rep" (fallback default)
  ✗ Org name is always "My Organization" with no way to change it
```

---

## Alternatives Considered

**A — Supabase database trigger**
Postgres trigger on `auth.users` insert that creates org + profile automatically.
- Can't easily access Google `full_name` metadata from a trigger
- Logic lives in SQL, disconnected from app code — harder to maintain
- Rejected

**B — Call `ensure_org` in every authenticated endpoint**
Add as a FastAPI dependency that runs on every request.
- Adds a DB read on every single request — wasteful
- Rejected

**C — Pass `full_name` to `ensure_org` to seed org name**
Modify `ensure_org` to accept the user's name and set org name on creation.
- Couples signup logic into `ensure_org`, which is a low-level utility
- Org name at creation time isn't that useful — user will want to change it anyway
- Rejected in favour of a dedicated rename endpoint

---

## Chosen Design

### Fix 1 — Role on first load (`POST /auth/init`)

New endpoint in `main.py` (too small for its own service file). Called from the
frontend after every login. Idempotent — does nothing if the org already exists.

```
POST /auth/init
Auth: required
Request: (none)
Response: { org_id: str, role: str }
```

`ensure_org` default role is changed from `owner` → `manager`. New solo signups
need call upload access; `manager` already includes billing access. The `owner`
role is reserved for a non-using billing admin in a team scenario (tracked in
GitHub Issues for future revisit).

**Frontend behaviour:** awaited before `loading` is set to `false` on `SIGNED_IN`.
The app does not render until `/auth/init` resolves, guaranteeing the org exists
before the user can interact with any feature. Since this is a fast DB read/write,
the added latency is negligible. `ensure_org` calls in upload paths are kept as a
silent fallback but should never be needed in practice.

### Fix 2 — Backfill existing profiles (migration 007)

One-time SQL migration to promote all existing `rep` rows to `manager`.
Existing users signed up before the lazy-init bug was fixed — they should
not be stuck as reps.

```sql
UPDATE user_profiles SET role = 'manager' WHERE role = 'rep';
```

Run once in Supabase SQL editor or as `migrations/007_backfill_roles.sql`.

### Fix 3 — Org rename (`PATCH /team/org`)

New endpoint in `team_service.py`. Restricted to `owner` and `manager` roles.

```
PATCH /team/org
Auth: required (owner or manager only)
Request: { name: str }
Response: { org_id: str, name: str }
```

Profile page gets a text field + save button for the org name, visible to
owners and managers only.

---

## Files to Change

| File | Change |
|------|--------|
| `python/api/database.py` | Change `ensure_org` default role `owner` → `manager` |
| `python/api/main.py` | Add `POST /auth/init` |
| `python/api/team_service.py` | Add `PATCH /team/org` |
| `python/api/models.py` | Add `OrgUpdateRequest` / `OrgResponse` models |
| `python/migrations/007_backfill_roles.sql` | Backfill existing `rep` → `manager` |
| `ui/wireframe/src/contexts/AuthContext.tsx` | Call `/auth/init` on `SIGNED_IN` |
| `ui/wireframe/src/pages/ProfilePage.tsx` | Add org name field for owner/manager |
| `ui/wireframe/src/services/api.ts` | Add `updateOrgName` API call |

---

## Status

- [x] `migrations/007_backfill_roles.sql` — backfill existing profiles
- [x] `database.py` — change `ensure_org` default role `owner` → `manager`
- [x] `main.py` — add `POST /auth/init`
- [x] `team_service.py` — add `PATCH /team/org`
- [x] `models.py` — add request/response models
- [x] `AuthContext.tsx` — call `/auth/init` on `SIGNED_IN`
- [x] `ProfilePage.tsx` — org name field for owner/manager
- [x] `api.ts` — `updateOrgName` helper