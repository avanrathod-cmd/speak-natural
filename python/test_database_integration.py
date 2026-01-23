"""
Test script to verify Supabase database integration.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from api.storage_manager import StorageManager
from api.database import DatabaseService

load_dotenv()


def test_database_integration():
    """Test the database integration end-to-end."""
    print("=" * 60)
    print("Testing Supabase Database Integration")
    print("=" * 60)

    # Initialize services
    print("\n1. Initializing StorageManager...")
    storage_manager = StorageManager()
    print("   ✓ StorageManager initialized")

    # Generate coaching ID
    print("\n2. Generating coaching ID...")
    coaching_id = storage_manager.generate_coaching_id()
    print(f"   ✓ Generated: {coaching_id}")

    # Create session directory
    print("\n3. Creating session directory...")
    directories = storage_manager.create_session_directory(coaching_id)
    print(f"   ✓ Created directories: {len(directories)} paths")

    # Create test user ID
    test_user_id = "123e4567-e89b-12d3-a456-426614174000"  # Example UUID

    # Save session metadata (this will create in database)
    print("\n4. Saving session metadata to database...")
    try:
        metadata = {
            "coaching_id": coaching_id,
            "user_id": test_user_id,
            "audio_filename": "test_audio.wav",
            "status": "pending",
            "directories": directories
        }
        storage_manager.save_session_metadata(coaching_id, metadata)
        print("   ✓ Session created in database")
    except Exception as e:
        print(f"   ✗ Failed to create session: {e}")
        return False

    # Load session metadata
    print("\n5. Loading session metadata from database...")
    loaded_metadata = storage_manager.load_session_metadata(coaching_id)
    if loaded_metadata:
        print(f"   ✓ Loaded session: {loaded_metadata['coaching_id']}")
        print(f"     - Status: {loaded_metadata['status']}")
        print(f"     - User ID: {loaded_metadata['user_id']}")
        print(f"     - Filename: {loaded_metadata['audio_filename']}")
    else:
        print("   ✗ Failed to load session")
        return False

    # Update session status
    print("\n6. Updating session status...")
    storage_manager.update_session_status(
        coaching_id,
        status="processing",
        progress="Testing progress update"
    )
    print("   ✓ Status updated to 'processing'")

    # Verify update
    loaded_metadata = storage_manager.load_session_metadata(coaching_id)
    if loaded_metadata["status"] == "processing":
        print(f"   ✓ Verified: status = {loaded_metadata['status']}")
    else:
        print(f"   ✗ Status mismatch: {loaded_metadata['status']}")
        return False

    # Save voice mapping
    print("\n7. Saving voice mapping...")
    voice_mapping = {
        "speaker_0": "voice_id_123",
        "speaker_1": "voice_id_456"
    }
    storage_manager.save_voice_mapping(coaching_id, voice_mapping)
    print("   ✓ Voice mapping saved")

    # Get voice mapping
    retrieved_mapping = storage_manager.get_voice_mapping(coaching_id)
    if retrieved_mapping == voice_mapping:
        print(f"   ✓ Verified: {len(retrieved_mapping)} speakers mapped")
    else:
        print("   ✗ Voice mapping mismatch")
        return False

    # List user sessions
    print("\n8. Listing user sessions...")
    user_sessions = storage_manager.list_sessions(user_id=test_user_id)
    print(f"   ✓ Found {len(user_sessions)} session(s) for user")
    if coaching_id in user_sessions:
        print(f"   ✓ Test session found in list")
    else:
        print("   ✗ Test session not in list")
        return False

    # List detailed sessions
    print("\n9. Listing detailed sessions...")
    detailed_sessions = storage_manager.list_sessions_detailed(user_id=test_user_id)
    print(f"   ✓ Retrieved {len(detailed_sessions)} detailed session(s)")
    for session in detailed_sessions:
        print(f"     - {session['coaching_id']}: {session['status']}")

    # Complete the session
    print("\n10. Completing session...")
    storage_manager.update_session_status(
        coaching_id,
        status="completed"
    )
    loaded_metadata = storage_manager.load_session_metadata(coaching_id)
    if loaded_metadata["status"] == "completed" and loaded_metadata.get("completed_at"):
        print(f"   ✓ Session completed at: {loaded_metadata['completed_at']}")
    else:
        print("   ✗ Session not properly completed")
        return False

    # Cleanup
    print("\n11. Cleaning up test session...")
    storage_manager.cleanup_session(coaching_id, keep_metadata=False)
    print("   ✓ Session deleted from database and local storage")

    # Verify deletion
    deleted_metadata = storage_manager.load_session_metadata(coaching_id)
    if deleted_metadata is None:
        print("   ✓ Verified: session no longer exists")
    else:
        print("   ✗ Session still exists after deletion")
        return False

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_database_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
