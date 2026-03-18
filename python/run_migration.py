"""
Run database migrations for Supabase.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add psycopg2 for direct PostgreSQL connection
try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    os.system("pip install psycopg2-binary")
    import psycopg2

load_dotenv()


def run_migration(migration_file: str):
    """Run a SQL migration file."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        sys.exit(1)

    # Read migration file
    migration_path = Path(__file__).parent / "migrations" / migration_file

    if not migration_path.exists():
        print(f"ERROR: Migration file not found: {migration_path}")
        sys.exit(1)

    with open(migration_path, 'r') as f:
        sql = f.read()

    print(f"Running migration: {migration_file}")
    print(f"Connecting to: {database_url.split('@')[1]}")  # Print without password

    # Connect and execute
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Execute the migration
        cur.execute(sql)
        conn.commit()

        print("✓ Migration completed successfully!")

        # Verify tables exist
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"\nTables in public schema: {', '.join(tables)}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: Failed to run migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migration = sys.argv[1] if len(sys.argv) > 1 else "001_create_coaching_sessions.sql"
    run_migration(migration)
