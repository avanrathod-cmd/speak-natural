#!/usr/bin/env python3
"""
Test client for SpeakRight Coaching API.

Example usage:
    python test_api_client.py path/to/audio.wav
"""

import sys
import requests
import time
from pathlib import Path


def test_coaching_api(audio_file_path: str, api_url: str = "http://localhost:8000"):
    """
    Test the complete coaching API workflow.

    Args:
        audio_file_path: Path to audio file
        api_url: API base URL
    """
    if not Path(audio_file_path).exists():
        print(f"❌ Error: Audio file not found: {audio_file_path}")
        return

    print("=" * 80)
    print("🎙️  SPEAKRIGHT COACHING API TEST")
    print("=" * 80)
    print(f"\nAPI URL: {api_url}")
    print(f"Audio file: {audio_file_path}")
    print()

    # Step 1: Health check
    print("[1/6] Health check...")
    try:
        response = requests.get(f"{api_url}/health")
        response.raise_for_status()
        print(f"✓ Server is healthy: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print("Make sure the server is running:")
        print("  python -m api.main --reload")
        return

    # Step 2: Upload audio
    print("\n[2/6] Uploading audio...")
    try:
        with open(audio_file_path, "rb") as f:
            files = {"audio_file": f}
            response = requests.post(f"{api_url}/upload-audio", files=files)
            response.raise_for_status()
            result = response.json()

        coaching_id = result["coaching_id"]
        print(f"✓ Audio uploaded successfully")
        print(f"  Coaching ID: {coaching_id}")
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return

    # Step 3: Poll status
    print(f"\n[3/6] Waiting for processing to complete...")
    print("  This may take 2-5 minutes...")

    max_attempts = 60  # 5 minutes at 5-second intervals
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(f"{api_url}/coaching/{coaching_id}/status")
            response.raise_for_status()
            status_data = response.json()

            status = status_data["status"]
            progress = status_data.get("progress", "")

            print(f"  [{attempt+1}] Status: {status} - {progress}")

            if status == "completed":
                print(f"✓ Processing complete!")
                print(f"  Completed at: {status_data.get('completed_at')}")
                break
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                print(f"❌ Processing failed: {error}")
                return

            time.sleep(5)
            attempt += 1

        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return

    if attempt >= max_attempts:
        print("❌ Timeout: Processing took too long")
        return

    # Step 4: Get metrics
    print(f"\n[4/6] Fetching metrics...")
    try:
        response = requests.get(f"{api_url}/coaching/{coaching_id}/metrics")
        response.raise_for_status()
        metrics = response.json()

        print(f"✓ Metrics retrieved:")
        print(f"  Overall Score: {metrics['overall_score']}/10")
        print(f"  Speaking Pace: {metrics['pace_wpm']:.1f} WPM")
        print(f"  Pitch Variation: {metrics['pitch_variation']}")
        print(f"  Energy Level: {metrics['energy_level']}")
        print(f"  Pause Count: {metrics['pause_distribution']['pause_count']}")
        print(f"  Avg Pause: {metrics['pause_distribution']['average_pause']:.2f}s")

    except Exception as e:
        print(f"❌ Failed to get metrics: {e}")

    # Step 5: Get feedback
    print(f"\n[5/6] Fetching coaching feedback...")
    try:
        response = requests.get(f"{api_url}/coaching/{coaching_id}/feedback")
        response.raise_for_status()
        feedback = response.json()

        print(f"✓ Coaching feedback retrieved:")
        print(f"\n  📊 General Feedback:")
        print(f"  {feedback['general_feedback'][:200]}...")

        if feedback['strong_points']:
            print(f"\n  💪 Strong Points:")
            for point in feedback['strong_points'][:3]:
                print(f"    • {point}")

        if feedback['improvements']:
            print(f"\n  🎯 Areas for Improvement:")
            for improvement in feedback['improvements'][:3]:
                print(f"    • {improvement}")

    except Exception as e:
        print(f"❌ Failed to get feedback: {e}")

    # Step 6: Download visualizations
    print(f"\n[6/6] Downloading visualizations...")
    viz_types = ["pitch", "intensity", "spectrogram"]
    downloaded = 0

    for viz_type in viz_types:
        try:
            response = requests.get(
                f"{api_url}/coaching/{coaching_id}/visualizations/{viz_type}"
            )
            response.raise_for_status()

            output_path = f"/tmp/{coaching_id}_{viz_type}.svg"
            with open(output_path, "wb") as f:
                f.write(response.content)

            print(f"  ✓ Downloaded {viz_type}.svg → {output_path}")
            downloaded += 1

        except Exception as e:
            print(f"  ⚠ Failed to download {viz_type}: {e}")

    print(f"\n✓ Downloaded {downloaded}/{len(viz_types)} visualizations")

    # Summary
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    print(f"\nCoaching ID: {coaching_id}")
    print(f"\nTo view all results:")
    print(f"  curl -O {api_url}/coaching/{coaching_id}/download")
    print(f"\nTo delete this session:")
    print(f"  curl -X DELETE {api_url}/coaching/{coaching_id}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api_client.py <audio_file> [api_url]")
        print("\nExample:")
        print("  python test_api_client.py audio.wav")
        print("  python test_api_client.py audio.wav http://localhost:8000")
        sys.exit(1)

    audio_file = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

    test_coaching_api(audio_file, api_url)
