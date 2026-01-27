# Supabase Database Migration

## Summary

Successfully migrated session metadata storage from local JSON files to Supabase PostgreSQL database. This provides persistent, scalable storage with proper user isolation and querying capabilities.

---

## What Changed

### Before
- Session metadata stored in local JSON files at `/tmp/speak-right/metadata/`
- Sessions listed by scanning filesystem
- No database-level user isolation
- Limited querying capabilities

### After
- Session metadata stored in Supabase PostgreSQL
- Fast database queries with proper indexing
- User-based session isolation at database level
- Supports complex queries and filtering
- Local JSON files kept as backup

---

## Database Schema

### Table: `coaching_sessions`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key (auto-generated) |
| coaching_id | TEXT | Unique session identifier (e.g., coach_abc123) |
| user_id | UUID | User who created the session (from JWT) |
| audio_filename | TEXT | Original audio filename |
| status | TEXT | Processing status: pending, processing, completed, failed |
| directories | JSONB | JSON object containing local directory paths |
| voice_mapping | JSONB | JSON mapping speaker labels to ElevenLabs voice IDs |
| progress | TEXT | Optional progress message |
| error | TEXT | Optional error message |
| created_at | TIMESTAMPTZ | Session creation time (auto) |
| updated_at | TIMESTAMPTZ | Last update time (auto-updated) |
| completed_at | TIMESTAMPTZ | Completion time (set when status=completed) |

### Indexes
- `idx_coaching_sessions_coaching_id` - Fast lookups by coaching_id
- `idx_coaching_sessions_user_id` - Fast filtering by user
- `idx_coaching_sessions_status` - Filter by status
- `idx_coaching_sessions_created_at` - Sorted queries

---

## Files Created/Modified

### New Files
1. **`python/api/database.py`** - DatabaseService class for Supabase operations
2. **`python/migrations/001_create_coaching_sessions.sql`** - SQL migration script
3. **`python/run_migration.py`** - Script to run database migrations
4. **`python/test_database_integration.py`** - Integration test suite

### Modified Files
1. **`python/api/storage_manager.py`**
   - Added `DatabaseService` integration
   - Methods now read/write to database
   - Local JSON files kept as backup
   - Added `list_sessions_detailed()` method

2. **`python/api/main.py`**
   - Updated `/sessions` endpoint to use database queries

3. **`python/.env`**
   - Added `SUPABASE_SERVICE_ROLE_KEY`
   - Added `DATABASE_URL` with proper URL encoding

---

## Environment Variables

Add to your `.env` file:

```bash
# Supabase Service Role Key (admin access - DO NOT expose to clients)
SUPABASE_SERVICE_ROLE_KEY=sb_secret_qVCSZe4rrShftDWPOkcbOA_ogBvlKwA

# PostgreSQL Database Connection
DATABASE_URL=postgresql://postgres:lambdakigpt%4012@db.zdyjozeuordbzvxfpecr.supabase.co:5432/postgres
```

---

## Usage

### StorageManager Methods (Updated)

```python
from api.storage_manager import StorageManager

storage = StorageManager()

# Create session (saves to database)
coaching_id = storage.generate_coaching_id()
metadata = {
    "coaching_id": coaching_id,
    "user_id": "user-uuid",
    "audio_filename": "audio.wav",
    "status": "pending"
}
storage.save_session_metadata(coaching_id, metadata)

# Load session (from database)
session = storage.load_session_metadata(coaching_id)

# Update status (updates database)
storage.update_session_status(
    coaching_id,
    status="processing",
    progress="Transcribing audio..."
)

# List user's sessions (database query)
sessions = storage.list_sessions(user_id="user-uuid")
detailed = storage.list_sessions_detailed(user_id="user-uuid")

# Voice mapping
storage.save_voice_mapping(coaching_id, {"speaker_0": "voice_id"})
mapping = storage.get_voice_mapping(coaching_id)

# Cleanup (deletes from database)
storage.cleanup_session(coaching_id, keep_metadata=False)
```

### Direct Database Access

```python
from api.database import DatabaseService

db = DatabaseService()

# Create session
db.create_session(
    coaching_id="coach_123",
    user_id="user-uuid",
    audio_filename="audio.wav"
)

# Get session
session = db.get_session("coach_123")

# Update status
db.update_session_status(
    "coach_123",
    status="completed",
    progress="Done!"
)

# List user sessions
sessions = db.list_user_sessions("user-uuid", limit=50)

# Delete session
db.delete_session("coach_123")
```

---

## Testing

Run the integration test:

```bash
cd python
python test_database_integration.py
```

This tests:
- Database connectivity
- Session creation
- Metadata updates
- Status changes
- Voice mapping
- Session listing
- Cleanup/deletion

---

## Migration Steps (Already Completed)

1. ✅ Created Supabase table schema
2. ✅ Ran migration to create `coaching_sessions` table
3. ✅ Updated StorageManager to use database
4. ✅ Updated API endpoints to use new methods
5. ✅ Tested integration end-to-end

---

## Benefits

### Performance
- Fast queries with proper indexing
- No filesystem scanning
- Efficient user-based filtering

### Scalability
- Handles millions of sessions
- Concurrent access without file locking
- Can be queried from multiple services

### Reliability
- ACID transactions
- Automatic backups (Supabase)
- No risk of corrupted JSON files

### Features
- Complex queries (filter by status, date range, etc.)
- Full-text search on metadata
- Aggregation queries (count by status, etc.)
- Real-time subscriptions (future feature)

---

## Backward Compatibility

The system maintains backward compatibility:
- Local JSON files still created as backup
- Can fallback to JSON if database unavailable
- Existing code continues to work

---

## Security

### Access Control
- Service role key used server-side only (admin access)
- Never expose service_role key to clients
- User sessions isolated by `user_id`

### Verification
```python
# Always verify user owns the session
session = db.get_session_by_user(coaching_id, user_id)
if not session:
    raise HTTPException(403, "Unauthorized")
```

---

## Next Steps (Optional)

### Future Enhancements
1. **Row Level Security (RLS)** - Add Postgres RLS policies for defense in depth
2. **Analytics** - Add queries for usage metrics and trends
3. **Soft Deletes** - Add `deleted_at` column instead of hard deletes
4. **Session History** - Track all status changes in separate table
5. **Search** - Add full-text search on transcripts
6. **Caching** - Add Redis layer for frequently accessed sessions

### Performance Optimizations
1. Connection pooling (asyncpg)
2. Read replicas for heavy read loads
3. Materialized views for analytics
4. Partition table by created_at for large datasets

---

## Troubleshooting

### Connection Issues
```bash
# Test database connection
python run_migration.py
```

### Check Table
```sql
-- In Supabase SQL editor
SELECT * FROM coaching_sessions LIMIT 10;
```

### Verify Indexes
```sql
SELECT * FROM pg_indexes WHERE tablename = 'coaching_sessions';
```

---

## Support

For issues or questions:
1. Check `/python/test_database_integration.py` for examples
2. View Supabase logs in dashboard
3. Check local JSON files as backup

---

**Migration completed successfully on 2026-01-22**
