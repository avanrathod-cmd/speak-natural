# database.py Refactor Plan

**Problem:** `database.py` is 1145 lines with ~35 single-purpose methods
that each hard-code a table name and a specific set of columns. Adding
new queries (like the export fetch) means adding yet another method.

**Goal:** Replace the per-query method explosion with four generic CRUD
primitives. Keep a small set of named helpers only where business logic
(multi-step writes, org bootstrapping) genuinely can't be expressed as a
single CRUD call.

---

## New Public Interface

```python
class DatabaseService:

    def get_rows(
        self,
        table: str,
        filters: dict | None = None,
        select: str = "*",
        order_by: str | None = None,
        ascending: bool = True,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]: ...

    def add_row(self, table: str, data: dict) -> dict: ...

    def update_rows(
        self,
        table: str,
        data: dict,
        filters: dict,
    ) -> list[dict]: ...

    def delete_rows(self, table: str, filters: dict) -> None: ...
```

### `filters` format

| Value type | Supabase call | Example |
|---|---|---|
| scalar | `.eq(col, val)` | `{"call_id": "call_abc"}` |
| list | `.in_(col, vals)` | `{"status": ["pending", "processing"]}` |
| `None` value | `.is_(col, "null")` | `{"error": None}` |

### Joins (Supabase PostgREST nested select)

Pass a nested select string — PostgREST resolves foreign keys
automatically:

```python
# replaces get_call_analysis()
db.get_rows(
    "sales_calls",
    filters={"call_id": call_id},
    select="*, call_analyses(*)",
)
# result[0] contains all sales_calls fields + nested call_analyses list
```

---

## Named Helpers to Keep

These involve multi-step writes or org-bootstrapping logic that
cannot collapse into a single CRUD call:

| Helper | Why it stays |
|---|---|
| `_ensure_org(user_id)` | Creates org + user_profile if missing; called before every write that needs org_id |
| `create_sales_call_from_attendee(...)` | Calls `_ensure_org` then inserts; callers catch IntegrityError for dedup |
| `create_product(...)` | Calls `_ensure_org` then inserts product + auto-generates script (two tables) |
| `save_call_analysis(...)` | Inserts into call_analyses with JSON serialisation of nested dicts |

All other methods (`get_call_analysis`, `list_sales_calls`,
`get_zoom_connection_id`, `get_user_email`, `is_webhook_key_processed`,
etc.) collapse to inline `get_rows` / `update_rows` calls at the
call site.

---

## Caller Changes

Both `sales_service.py` and `attendee_service.py` call `_db.*`.
Each call site becomes a direct `get_rows` / `update_rows` / etc.
call with the appropriate table name and filters.

Example — current:
```python
row = _db.get_call_analysis(call_id)
```
After refactor:
```python
rows = _db.get_rows(
    "sales_calls",
    filters={"call_id": call_id},
    select="*, call_analyses(*)",
)
row = rows[0] if rows else None
# flatten nested call_analyses if present
if row and row.get("call_analyses"):
    row.update(row.pop("call_analyses")[0])
```

---

## Files Touched

| File | Change |
|---|---|
| `python/api/database.py` | Full rewrite — keep 4 CRUD methods + 4 named helpers above |
| `python/api/sales_service.py` | Update all `_db.*` call sites |
| `python/api/attendee_service.py` | Update all `_db.*` call sites |

`python/api/models.py` and service logic are untouched.

---

## Out of Scope

- No changes to table schemas or migrations
- No changes to callers outside `api/`
- The old coaching-session methods (`create_session`, `get_session`,
  etc.) at the top of the file — kept as-is or collapsed to CRUD
  calls, whichever is cleaner; they're low-traffic

---

## Open Question

The nested select flattening (merging `call_analyses` into the parent
row) happens in ~3 places today. Should that flattening live in a small
`_merge_nested(row, key)` private helper, or inline at each call site?
Recommendation: inline — three sites is not enough repetition to
justify a helper.