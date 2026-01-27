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

        # Verify table was created
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'coaching_sessions'
        """)

        result = cur.fetchone()
        if result:
            print(f"✓ Table 'coaching_sessions' exists")

            # Show table structure
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'coaching_sessions'
                ORDER BY ordinal_position
            """)

            columns = cur.fetchall()
            print("\nTable structure:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: Failed to run migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the first migration
    run_migration("001_create_coaching_sessions.sql")
