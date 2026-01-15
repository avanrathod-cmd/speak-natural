"""
FastAPI server for speech coaching service.

Provides endpoints for:
- Upload audio and generate coaching
- Get coaching status
- Retrieve metrics and feedback
- Download processed audio segments
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Optional
import json
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from api.models import (
    UploadAudioResponse,
    CoachingStatusResponse,
    MetricsResponse,
    SegmentResponse,
    CoachingFeedbackResponse,
    ErrorResponse,
    SignupRequest,
    SignupResponse
)
from api.storage_manager import StorageManager
from services.audio_processor import AudioProcessorService

# Initialize FastAPI app
app = FastAPI(
    title="SpeakRight Coaching API",
    description="AI-powered speech coaching and analysis service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
storage_manager = StorageManager(base_dir=os.getenv("STORAGE_DIR", "/tmp/speak-right"))
audio_processor = AudioProcessorService(bucket_name=os.getenv("S3_BUCKET", "speach-analyzer"))


# Background task for processing audio
def process_audio_background(coaching_id: str, audio_file_path: str):
    """
    Background task to process audio file.

    Args:
        coaching_id: Coaching session ID
        audio_file_path: Path to audio file
    """
    try:
        # Update status to processing
        storage_manager.update_session_status(
            coaching_id,
            status="processing",
            progress="Starting audio processing..."
        )

        # Process audio
        results = audio_processor.process_audio_file(
            audio_file_path=audio_file_path,
            request_id=coaching_id,
            output_base_dir=storage_manager.base_dir,
            skip_coaching=False
        )

        # Update metadata with results
        metadata = storage_manager.load_session_metadata(coaching_id)
        metadata.update(results)
        storage_manager.save_session_metadata(coaching_id, metadata)

        # Update status to completed
        storage_manager.update_session_status(
            coaching_id,
            status="completed",
            progress="Processing complete"
        )

    except Exception as e:
        # Update status to failed
        storage_manager.update_session_status(
            coaching_id,
            status="failed",
            error=str(e)
        )
        print(f"Error processing audio for {coaching_id}: {e}")
        import traceback
        traceback.print_exc()


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "service": "SpeakRight Coaching API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/auth/signup", response_model=SignupResponse, tags=["Authentication"])
async def signup(request: SignupRequest):
    """
    Mock signup endpoint.

    In production, this should:
    - Validate email and password
    - Hash password
    - Store user in database
    - Generate JWT token
    """
    import uuid

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    mock_token = f"token_{uuid.uuid4().hex}"

    return SignupResponse(
        user_id=user_id,
        email=request.email,
        token=mock_token,
        message="Signup successful (mock)"
    )


@app.post("/upload-audio", response_model=UploadAudioResponse, tags=["Audio Processing"])
async def upload_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    user_id: Optional[str] = Query(None, description="Optional user ID")
):
    """
    Upload audio file and start coaching analysis.

    Steps:
    1. Generate coaching_id
    2. Save audio file locally
    3. Start background processing task
    4. Return coaching_id immediately

    Args:
        audio_file: Audio file (WAV, MP3, etc.)
        user_id: Optional user ID for tracking

    Returns:
        Coaching ID and status
    """
    # Generate coaching ID
    coaching_id = storage_manager.generate_coaching_id()

    # Create session directories
    directories = storage_manager.create_session_directory(coaching_id)

    # Save uploaded file
    input_dir = directories["input"]
    audio_filename = audio_file.filename or "audio.wav"
    audio_path = os.path.join(input_dir, audio_filename)

    try:
        # Save file to disk
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # Initialize metadata
        metadata = {
            "coaching_id": coaching_id,
            "user_id": user_id,
            "audio_filename": audio_filename,
            "audio_path": audio_path,
            "status": "pending",
            "directories": directories
        }
        storage_manager.save_session_metadata(coaching_id, metadata)

        # Add background task
        background_tasks.add_task(process_audio_background, coaching_id, audio_path)

        return UploadAudioResponse(
            coaching_id=coaching_id,
            status="pending",
            message="Audio uploaded successfully. Processing started."
        )

    except Exception as e:
        # Clean up on error
        storage_manager.cleanup_session(coaching_id)
        raise HTTPException(status_code=500, detail=f"Error uploading audio: {str(e)}")


@app.get("/coaching/{coaching_id}/status", response_model=CoachingStatusResponse, tags=["Coaching"])
async def get_coaching_status(coaching_id: str):
    """
    Get coaching session status.

    Args:
        coaching_id: Coaching session ID

    Returns:
        Status information
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    return CoachingStatusResponse(
        coaching_id=coaching_id,
        status=metadata.get("status", "unknown"),
        progress=metadata.get("progress"),
        created_at=metadata.get("created_at"),
        completed_at=metadata.get("completed_at"),
        error=metadata.get("error")
    )


@app.get("/coaching/{coaching_id}/metrics", response_model=MetricsResponse, tags=["Coaching"])
async def get_coaching_metrics(coaching_id: str):
    """
    Get overall speech metrics for a coaching session.

    Args:
        coaching_id: Coaching session ID

    Returns:
        Speech metrics including score, pace, pitch, energy, pauses
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    # Try to load structured metrics first (new format)
    try:
        session_dir = storage_manager.get_session_directory(coaching_id)
        structured_metrics_path = os.path.join(session_dir, "output", "metrics", "structured_metrics.json")

        if os.path.exists(structured_metrics_path):
            with open(structured_metrics_path, 'r') as f:
                structured_metrics = json.load(f)

            return MetricsResponse(
                coaching_id=coaching_id,
                overall_score=structured_metrics["overall_score"],
                pace_wpm=structured_metrics["pace"]["words_per_minute"],
                pitch_variation=structured_metrics["pitch_variation"]["rating"],
                energy_level=structured_metrics["energy_level"]["rating"],
                pause_distribution={
                    "pause_count": structured_metrics["pause_distribution"]["pause_count"],
                    "total_pause_duration": structured_metrics["pause_distribution"]["total_duration_seconds"],
                    "average_pause": structured_metrics["pause_distribution"]["average_duration_seconds"]
                }
            )

    except Exception as e:
        print(f"Could not load structured metrics: {e}, falling back to legacy calculation")

    # Fallback: Load analysis results and calculate on-the-fly (old format)
    try:
        analysis_path = metadata["analysis"]["analysis"]
        with open(analysis_path, 'r') as f:
            analysis_data = json.load(f)

        speech_metrics = analysis_data["speech_metrics"]
        acoustic_features = analysis_data["acoustic_features"]

        # Calculate ratings
        pitch_range = acoustic_features["parselmouth"]["pitch_range_hz"]
        pitch_variation = "good" if pitch_range > 100 else "moderate" if pitch_range > 50 else "needs improvement"

        intensity_std = acoustic_features["parselmouth"]["intensity_std_db"]
        energy_level = "good" if intensity_std > 5 else "moderate" if intensity_std > 3 else "low"

        # Overall score calculation (simple heuristic)
        score = 5.0
        score += min(2.0, speech_metrics["speaking_rate_wpm"] / 75)  # Target ~150 WPM
        score -= speech_metrics["filler_word_ratio"] * 10
        score += min(2.0, pitch_range / 100)
        score = max(0, min(10, score))

        return MetricsResponse(
            coaching_id=coaching_id,
            overall_score=round(score, 1),
            pace_wpm=speech_metrics["speaking_rate_wpm"],
            pitch_variation=pitch_variation,
            energy_level=energy_level,
            pause_distribution={
                "pause_count": speech_metrics["pause_count"],
                "total_pause_duration": speech_metrics["total_pause_duration_seconds"],
                "average_pause": speech_metrics["average_pause_seconds"]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading metrics: {str(e)}")


@app.get("/coaching/{coaching_id}/metrics/detailed", tags=["Coaching"])
async def get_detailed_metrics(coaching_id: str):
    """
    Get detailed structured metrics with definitions and AI insights.

    Args:
        coaching_id: Coaching session ID

    Returns:
        Full structured metrics JSON with ratings, definitions, and AI analysis
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    try:
        session_dir = storage_manager.get_session_directory(coaching_id)
        structured_metrics_path = os.path.join(session_dir, "output", "metrics", "structured_metrics.json")

        if not os.path.exists(structured_metrics_path):
            raise HTTPException(status_code=404, detail="Structured metrics not available")

        with open(structured_metrics_path, 'r') as f:
            structured_metrics = json.load(f)

        return {
            "coaching_id": coaching_id,
            "metrics": structured_metrics
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading detailed metrics: {str(e)}")


@app.get("/coaching/{coaching_id}/feedback", response_model=CoachingFeedbackResponse, tags=["Coaching"])
async def get_coaching_feedback(coaching_id: str):
    """
    Get detailed coaching feedback with segments.

    Args:
        coaching_id: Coaching session ID

    Returns:
        Detailed feedback and segment analysis
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    try:
        # Load coaching feedback
        coaching_feedback_path = metadata["analysis"].get("coaching_feedback")

        if not coaching_feedback_path or not os.path.exists(coaching_feedback_path):
            raise HTTPException(status_code=404, detail="Coaching feedback not available")

        with open(coaching_feedback_path, 'r') as f:
            feedback_content = f.read()

        # Parse feedback (simple parsing, can be enhanced)
        lines = feedback_content.split('\n')
        general_feedback = []
        strong_points = []
        improvements = []

        current_section = None
        for line in lines:
            line = line.strip()
            if "general feedback" in line.lower():
                current_section = "general"
            elif "strong points" in line.lower() or "strengths" in line.lower():
                current_section = "strong"
            elif "improvement" in line.lower() or "areas to improve" in line.lower():
                current_section = "improvements"
            elif line and not line.startswith('#'):
                if current_section == "general":
                    general_feedback.append(line)
                elif current_section == "strong":
                    strong_points.append(line.lstrip('- '))
                elif current_section == "improvements":
                    improvements.append(line.lstrip('- '))

        # Create segments (simplified)
        segments = []
        # TODO: Parse actual segments from analysis

        return CoachingFeedbackResponse(
            coaching_id=coaching_id,
            general_feedback='\n'.join(general_feedback) or feedback_content[:500],
            strong_points=strong_points or ["Analysis complete"],
            improvements=improvements or ["See detailed feedback"],
            segments=segments
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading feedback: {str(e)}")


@app.get("/coaching/{coaching_id}/visualizations/{viz_type}", tags=["Coaching"])
async def get_visualization(coaching_id: str, viz_type: str):
    """
    Get visualization file (SVG).

    Args:
        coaching_id: Coaching session ID
        viz_type: Visualization type (pitch, intensity, spectrogram, etc.)

    Returns:
        SVG file
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    # Find visualization file
    viz_dir = metadata["analysis"]["visualizations"]
    viz_files = list(Path(viz_dir).glob(f"*{viz_type}*.svg"))

    if not viz_files:
        raise HTTPException(status_code=404, detail=f"Visualization not found: {viz_type}")

    return FileResponse(
        path=str(viz_files[0]),
        media_type="image/svg+xml",
        filename=viz_files[0].name
    )


@app.get("/coaching/{coaching_id}/download", tags=["Coaching"])
async def download_all_results(coaching_id: str):
    """
    Download all results as a zip file.

    Args:
        coaching_id: Coaching session ID

    Returns:
        Zip file with all results
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    # Create zip file
    session_dir = storage_manager.get_session_directory(coaching_id)
    zip_path = f"/tmp/{coaching_id}.zip"

    try:
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', session_dir)

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{coaching_id}_results.zip",
            headers={
                "Content-Disposition": f"attachment; filename={coaching_id}_results.zip"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating zip: {str(e)}")


@app.delete("/coaching/{coaching_id}", tags=["Coaching"])
async def delete_coaching_session(coaching_id: str, keep_s3: bool = Query(True)):
    """
    Delete coaching session.

    Args:
        coaching_id: Coaching session ID
        keep_s3: Whether to keep S3 files (default: True)

    Returns:
        Deletion status
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    # Clean up local files
    storage_manager.cleanup_session(coaching_id, keep_metadata=False)

    # TODO: Optionally delete S3 files if keep_s3=False

    return {"message": f"Coaching session {coaching_id} deleted", "s3_files_kept": keep_s3}


@app.get("/sessions", tags=["Coaching"])
async def list_sessions(user_id: Optional[str] = Query(None)):
    """
    List all coaching sessions (optionally filtered by user).

    Args:
        user_id: Optional user ID filter

    Returns:
        List of coaching sessions
    """
    all_sessions = storage_manager.list_sessions()

    sessions_info = []
    for coaching_id in all_sessions:
        metadata = storage_manager.load_session_metadata(coaching_id)
        if user_id is None or metadata.get("user_id") == user_id:
            sessions_info.append({
                "coaching_id": coaching_id,
                "status": metadata.get("status"),
                "created_at": metadata.get("created_at"),
                "completed_at": metadata.get("completed_at")
            })

    return {"sessions": sessions_info, "count": len(sessions_info)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run SpeakRight Coaching API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
