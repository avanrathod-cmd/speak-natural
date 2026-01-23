"""
Verify the complete authentication and database flow.
Shows how email → user_id → sessions works.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def verify_auth_flow():
    """Verify the auth flow is working correctly."""
    print("=" * 60)
    print("Verifying Authentication & Database Flow")
    print("=" * 60)

    # Initialize Supabase client with service role (admin access)
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    supabase = create_client(supabase_url, service_role_key)

    print("\n1. Checking Supabase auth.users table...")
    try:
        # List users (admin operation)
        response = supabase.auth.admin.list_users()
        users = response

        print(f"   ✓ Found {len(users)} user(s) in auth.users")

        if len(users) > 0:
            print("\n   Users in system:")
            for user in users[:5]:  # Show first 5
                email = user.email
                user_id = user.id
                created = str(user.created_at)[:10] if hasattr(user, 'created_at') else 'N/A'
                print(f"     - {email} → {user_id} (created: {created})")
        else:
            print("   ℹ No users registered yet (auth.users is empty)")

    except Exception as e:
        print(f"   ✗ Error accessing auth.users: {e}")
        return False

    print("\n2. Checking coaching_sessions table...")
    try:
        from api.database import DatabaseService
        db = DatabaseService()

        sessions = db.list_all_sessions(limit=10)
        print(f"   ✓ Found {len(sessions)} session(s) in coaching_sessions")

        if len(sessions) > 0:
            print("\n   Sessions in database:")
            for session in sessions[:5]:  # Show first 5
                coaching_id = session['coaching_id']
                user_id = session['user_id']
                status = session['status']
                created = str(session['created_at'])[:10]
                print(f"     - {coaching_id} → user:{user_id} [{status}] (created: {created})")
        else:
            print("   ℹ No sessions created yet (coaching_sessions is empty)")

    except Exception as e:
        print(f"   ✗ Error accessing coaching_sessions: {e}")
        return False

    print("\n3. Verifying user → session relationships...")
    if len(users) > 0 and len(sessions) > 0:
        # Check if any sessions belong to registered users
        user_ids = {str(user.id) for user in users}
        session_user_ids = {str(session['user_id']) for session in sessions}

        matching = user_ids & session_user_ids
        if matching:
            print(f"   ✓ Found {len(matching)} user(s) with sessions")
            for user_id in list(matching)[:3]:
                user = next((u for u in users if str(u.id) == user_id), None)
                user_sessions = [s for s in sessions if str(s['user_id']) == user_id]
                if user:
                    print(f"     - {user.email} has {len(user_sessions)} session(s)")
        else:
            print("   ℹ No sessions match registered users yet")
    else:
        print("   ℹ Skipped (need both users and sessions)")

    print("\n" + "=" * 60)
    print("✓ Verification Complete!")
    print("=" * 60)

    print("\nFlow Summary:")
    print("  1. User signs up → Supabase creates entry in auth.users")
    print("  2. User logs in → Gets JWT token with user_id")
    print("  3. User uploads audio → Backend extracts user_id from JWT")
    print("  4. Backend creates session in coaching_sessions with user_id")
    print("  5. User lists sessions → Backend filters by user_id from JWT")

    return True


if __name__ == "__main__":
    try:
        verify_auth_flow()
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
