# Admin CLI Plan

## Overview

A single `python/scripts/admin.py` CLI for operational tasks that are
non-trivial or impossible to trigger via the UI. All commands talk directly
to Supabase (via the service role key, bypassing RLS) and S3. Destructive
commands require explicit `--confirm` or interactive prompt.

---

## Tech Stack

- **CLI framework:** `typer` (already in uv ecosystem, rich output, nested
  subcommands, auto `--help`)
- **DB access:** `supabase-py` with `SUPABASE_SERVICE_ROLE_KEY` (same env
  vars as the API)
- **S3 access:** `boto3` (already used by the processor)
- **Output:** plain tables via `rich` (bundled with typer)

No new dependencies needed beyond adding `typer[all]` to `pyproject.toml`.

---

## File Structure

```
python/scripts/
└── admin.py          # single entry point, all subcommands here
```

Run via: `uv run python scripts/admin.py <group> <command> [args]`

---

## Environment Variables Required

Same as the API:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (not the anon key — needs full DB access)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `S3_BUCKET_NAME`

---

## Command Groups & Commands

### `org` — Organization management

#### `org list`
List all orgs with summary stats.

**Output columns:** org_id, name, plan, status, seat_limit, users,
calls, created_at

**DB queries:**
- `SELECT * FROM organizations`
- JOIN `subscriptions` on org_id
- COUNT `user_profiles` grouped by org_id
- COUNT `sales_calls` grouped by org_id

---

#### `org report <org_id>`
Detailed usage report for one org.

**Output:**
- Org name, created_at
- Subscription: plan, status, seat_limit, current_period_end,
  dodo_customer_id
- Users: list of (user_id, full_name, role, created_at)
- Pending invites: (email, role, expires_at)
- Calls: total, by status (completed/failed/processing/pending),
  last 30 days
- Avg scores (overall_rep_score, lead_score) across completed calls
- Products + scripts count

---

#### `org delete <org_id>`
Hard delete an org and all its data. **Destructive — irreversible.**

**Confirmation:** prints summary of what will be deleted, requires
typing org name to confirm.

**Deletion order (respects FK constraints):**
1. Delete S3 objects: list all `s3://speach-analyzer/sales/<call_id>/`
   prefixes for calls in this org, then delete each
2. `DELETE FROM call_analyses WHERE org_id = ?`
3. `DELETE FROM sales_calls WHERE org_id = ?`
4. `DELETE FROM manager_chat_messages WHERE chat_session_id IN
   (SELECT id FROM manager_chat_sessions WHERE org_id = ?)`
5. `DELETE FROM manager_chat_sessions WHERE org_id = ?`
6. `DELETE FROM sales_scripts WHERE org_id = ?`
7. `DELETE FROM products WHERE org_id = ?`
8. `DELETE FROM org_invites WHERE org_id = ?`
9. `DELETE FROM subscriptions WHERE org_id = ?`
10. `SET org_id = NULL ON user_profiles WHERE org_id = ?`
    (cannot delete user_profiles rows — auth.users is owned by Supabase
    Auth; users themselves must be deleted via Supabase dashboard or
    Auth Admin API separately)
11. `DELETE FROM organizations WHERE id = ?`

**Note on Supabase Auth users:** This CLI nulls out their `org_id` and
sets `role = 'rep'` but does NOT delete the `auth.users` row. That must
be done separately via the Supabase dashboard or a follow-up using the
Auth Admin API. A post-deletion message will remind the operator.

---

### `sub` — Subscription management

#### `sub status <org_id>`
Print current subscription state.

**Output:** plan, status, seat_limit, current_period_end,
dodo_customer_id, dodo_subscription_id, seats_used (count of active
manager+rep+owner rows)

---

#### `sub fix <org_id>`
Manually override subscription fields. Used for support cases, test
accounts, or when Dodo webhook didn't fire.

**Options:**
- `--plan [free|solo|team|unlimited]`
- `--status [active|cancelled|failed|expired]`
- `--seat-limit <int>`
- `--period-end <YYYY-MM-DD>` (sets current_period_end)

**Behavior:** Updates `subscriptions` row for the org. Prints before/after
diff. Requires `--confirm`.

**DB query:** `UPDATE subscriptions SET ... WHERE org_id = ?`

---

### `user` — User management

#### `user remove <user_id>`
Remove a user from their org. Sets `org_id = NULL` and `role = 'rep'`
in `user_profiles`. Does not delete the auth user.

**Output:** shows user's current org + role before removal.
Requires `--confirm`.

---

#### `user role <user_id> --role <owner|manager|rep>`
Change a user's role within their current org.

**Validation:** If promoting to `owner`/`manager` and org is at seat
limit, warn and abort (unless `--force`).

**DB query:** `UPDATE user_profiles SET role = ? WHERE id = ?`

---

### `invite` — Invite management

#### `invite list <org_id>`
List pending (not yet accepted, not expired) invites for an org.

**Output columns:** email, role, created_at, expires_at, created_by

---

#### `invite expire <org_id>`
Immediately expire all pending invites for an org by setting
`expires_at = NOW()`.

**Use case:** suspected leaked invite links, org offboarding.
Requires `--confirm`.

**DB query:**
`UPDATE org_invites SET expires_at = NOW() WHERE org_id = ? AND accepted_at IS NULL`

---

### `call` — Call data management

#### `call list <org_id>`
List calls for an org with status breakdown.

**Options:**
- `--status [pending|processing|completed|failed]` (filter)
- `--limit <int>` (default 50)

**Output columns:** call_id, rep_id, status, duration_seconds, created_at,
error (if failed)

---

#### `call repair <org_id>`
Find all calls stuck in `processing` status (older than 30 min) and
reset them to `pending` so they can be retried.

**Logic:**
- `SELECT * FROM sales_calls WHERE org_id = ? AND status = 'processing'
  AND updated_at < NOW() - INTERVAL '30 minutes'`
- For each: `UPDATE sales_calls SET status = 'pending', error = NULL
  WHERE call_id = ?`
- Prints count of repaired calls.

**Note:** Does not re-trigger processing — the API's background task
runner must be separately invoked (or the processing loop will pick
them up on next poll). A future enhancement could POST to
`/calls/{call_id}/reanalyze` for each.

---

#### `call reanalyze <org_id>`
Bulk-reanalyze all completed calls for an org. Useful after LLM model
upgrades or analysis bug fixes.

**Options:**
- `--since <YYYY-MM-DD>` (only calls created after this date)
- `--dry-run` (prints which calls would be reanalyzed without doing it)

**Logic:**
- Fetches all `completed` calls for the org (filtered by `--since`)
- For each call: POSTs to `POST /calls/{call_id}/reanalyze` on the
  running API (URL read from `API_BASE_URL` env var)
- Rate-limits to 2 concurrent requests to avoid overloading the LLM

**Auth:** Uses a service-level API token (or `SUPABASE_SERVICE_ROLE_KEY`
directly if the endpoint supports it).

---

#### `call cleanup-s3`
Find S3 objects under `sales/` that have no matching `sales_calls` row
and delete them.

**Logic:**
1. List all S3 keys under `s3://speach-analyzer/sales/`
2. Extract `call_id` from each key path (`sales/<call_id>/...`)
3. Query DB: `SELECT call_id FROM sales_calls WHERE call_id IN (?)`
4. S3 keys whose `call_id` is not in DB are orphans
5. Print orphan list; delete with `--confirm`

**Options:**
- `--dry-run` (list orphans without deleting)

---

### `gdpr` — Compliance operations

#### `gdpr export <user_id>`
Export all personal data for a user as a JSON file. For GDPR data
subject access requests.

**Data collected:**
- `user_profiles` row
- All `sales_calls` where `rep_id = ?`
- All `call_analyses` for those calls
- All `org_invites` where created_by = user_id
- All `manager_chat_sessions` + `manager_chat_messages` for the user

**Output:** writes `gdpr_export_<user_id>_<date>.json` to current
directory.

---

#### `gdpr delete <user_id>`
Erase all personal data for a user (GDPR right to erasure).
**Irreversible.**

**Confirmation:** requires typing user's email to confirm.

**Steps:**
1. Fetch user's `call_id` list from `sales_calls WHERE rep_id = ?`
2. Delete S3 audio/transcript objects for those calls
3. `DELETE FROM call_analyses WHERE call_id IN (?)`
4. `DELETE FROM sales_calls WHERE rep_id = ?`
5. `DELETE FROM manager_chat_messages WHERE chat_session_id IN
   (SELECT id FROM manager_chat_sessions WHERE manager_id = ?)`
6. `DELETE FROM manager_chat_sessions WHERE manager_id = ?`
7. `DELETE FROM org_invites WHERE created_by = ?`
8. `DELETE FROM user_profiles WHERE id = ?`
9. Prints reminder to delete `auth.users` row via Supabase Auth Admin API

---

## Error Handling

- All commands catch DB/S3 exceptions and print a clean error message
  with the raw exception detail in `--verbose` mode.
- Destructive commands wrap multi-step operations in a try/except; on
  failure they print which step failed and how many rows were already
  affected, so the operator knows the exact state.
- No automatic rollback (Supabase HTTP client doesn't expose
  transactions) — the plan doc for each command lists steps in an order
  that minimizes orphan risk if interrupted mid-way.

---

## Implementation Phases

### Phase 1 — Foundation + highest-value commands
1. Scaffold `admin.py` with `typer` app, env var loading, DB + S3 client init
2. `org list` and `org report` (read-only, safe to ship first)
3. `org delete` (the original request)
4. `sub status` and `sub fix`

### Phase 2 — User + invite management
5. `user remove` and `user role`
6. `invite list` and `invite expire`

### Phase 3 — Call operations
7. `call list` and `call repair`
8. `call reanalyze`
9. `call cleanup-s3`

### Phase 4 — Compliance
10. `gdpr export`
11. `gdpr delete`

---

## Open Questions

1. **Auth for `call reanalyze`:** Should it call the live API (needs
   `API_BASE_URL`) or replicate the analysis logic inline? Calling the
   API is simpler but couples the CLI to a running server.

2. **Auth user deletion:** Supabase Auth Admin API requires the service
   role key and a separate HTTP call. Should `org delete` / `gdpr delete`
   attempt this automatically, or always leave it as a manual step with
   a printed reminder?

3. **Logging:** Should destructive operations write an audit log (e.g.,
   append to a local `admin_audit.log` or a DB table)?

4. **Packaging:** Should `admin.py` be runnable as `uv run admin` via a
   `[project.scripts]` entry in `pyproject.toml`, or is
   `uv run python scripts/admin.py` sufficient?