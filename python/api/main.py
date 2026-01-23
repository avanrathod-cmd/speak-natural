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

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
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
    TranscriptWithSegmentsResponse,
    CoachingFeedbackResponse,
    ErrorResponse,
    SignupRequest,
    SignupResponse,
    PracticeTheme,
    PracticeThemesResponse,
    PracticeDialogueResponse
)
from api.storage_manager import StorageManager
from services.audio_processor import AudioProcessorService
from api.auth import get_current_user, get_current_user_optional
from services.waveform_generator import generate_waveform_data
from services.segment_generator import generate_segments_with_audio
from utils.aws_utils import s3_client

# Initialize FastAPI app
app = FastAPI(
    title="SpeakRight Coaching API",
    description="AI-powered speech coaching and analysis service",
    version="1.0.0"
)

# Add CORS middleware
# Get allowed origins from environment variable or allow all for development
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = ["*"] if allowed_origins_str == "*" else allowed_origins_str.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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


@app.get("/auth/verify", tags=["Authentication"])
async def verify_auth(user: dict = Depends(get_current_user)):
    """
    Verify authentication token.

    Use this endpoint to test if your Supabase JWT token is valid.

    Returns:
        User information from token
    """
    return {
        "authenticated": True,
        "user_id": user["user_id"],
        "email": user.get("email"),
        "role": user.get("role")
    }


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


# Practice themes and dialogues data
PRACTICE_THEMES = [
    PracticeTheme(
        id="dialogue",
        name="Dialogue Practice",
        description="Practice natural conversation and interpersonal communication",
        icon="MessageSquare"
    ),
    PracticeTheme(
        id="sales_pitch",
        name="Sales Pitch",
        description="Deliver a compelling product or service pitch",
        icon="TrendingUp"
    ),
    PracticeTheme(
        id="presentation",
        name="Presentation",
        description="Present ideas clearly and professionally",
        icon="PlayCircle"
    ),
]

PRACTICE_DIALOGUES = {
    "dialogue": '''
    "It’s been eighty-four years, and I can **still** smell the fresh paint. The china had **never** been used. The sheets had never been slept in. Titanic was called the ship of **dreams**, and it 
**really** was. To everyone else, it was the **largest** vessel ever built, a triumph of human 
engineering. But to **me**, it was a **slave** ship, taking me back to America in **chains**. 
Outwardly, I was **everything** a well-brought-up girl should be. Inside, I was **screaming**. 
Then I met **Jack**. He saved me in **every** way that a person can be saved. I don't **even** have a picture of him now. He exists **only** in my memory. I’ve kept his story locked **deep** inside for decades. But **now**, you all need to know what **really** happened on that fateful 
night out in the middle of the Atlantic Ocean. It was more than just a tragedy; it was the 
**end** of an era for all of us who were there."

''',

    "sales_pitch": '''
"Let’s be **honest**. Your current laptop is **dragging** you down. You feel it every time it 
stutters during a render or suddenly **dies** right before a major deadline. That ends **today**. 
Introducing the Apex Ultra. This isn't just a computer; it is a **total** powerhouse. We 
packed it with a ten-core processor that **demolishes** every single task you throw at it. 
The screen? It is a Pro-Motion OLED with billions of colors that **literally** pop off the glass. 
It is so **light** you will forget it is in your bag, yet the battery lasts for **twenty** hours. 
Imagine working from a cafe or an airplane without **ever** hunting for a plug. If you are 
**serious** about your career, you deserve a tool that actually **works** as hard as **you** do. 
Don’t wait another minute to **finally** upgrade your entire life and workflow. This is the 
machine you have been **waiting** for."

''',

    "presentation": '''
"Good morning, everyone. I am **incredibly** proud to stand here today. Our third-quarter 
results are finally in, and the news is **stunning**. We didn’t just **hit** our revenue 
targets; we **shattered** them by fifteen percent. Our expansion into the European market has 
been a **massive** success, surpassing even our most **optimistic** projections. But numbers 
only tell **part** of the story. The **real** win is the efficiency of our engineering team. 
You reduced our server latency by **half** while simultaneously **cutting** costs. That is 
**unheard** of in this industry. As we look toward the future, our pipeline for the next six 
months is the **strongest** it has ever been. We are perfectly positioned to **dominate** the 
market space. I want to **personally** thank every one of you for your unwavering dedication 
to this vision. Let’s keep this momentum going **strong** into the new year."
''',
}


def count_dialogue_words(text: str) -> int:
    """Count words in dialogue text, excluding markdown syntax."""
    clean_text = text.replace("**", "")
    return len([word for word in clean_text.split() if word])


@app.get("/practice/themes", response_model=PracticeThemesResponse, tags=["Practice"])
async def get_practice_themes(user: dict = Depends(get_current_user_optional)):
    """
    Get available practice themes.

    **Authentication Optional**: Works with or without authentication.

    Returns:
        List of available practice themes (Dialogue, Sales Pitch, Presentation)
    """
    return PracticeThemesResponse(themes=PRACTICE_THEMES)


@app.get("/practice/dialogue/{theme_id}", response_model=PracticeDialogueResponse, tags=["Practice"])
async def get_practice_dialogue(
    theme_id: str,
    user: dict = Depends(get_current_user_optional)
):
    """
    Get a practice dialogue for a specific theme.

    **Authentication Optional**: Works with or without authentication.

    Args:
        theme_id: Theme identifier (dialogue, sales_pitch, presentation)

    Returns:
        Dialogue text with **bold** markers for emphasis words/phrases

    Example Response:
    {
      "theme_id": "sales_pitch",
      "theme_name": "Sales Pitch",
      "dialogue": "Good morning... **transform** how your teams work...",
      "word_count": 185
    }
    """
    if theme_id not in PRACTICE_DIALOGUES:
        raise HTTPException(
            status_code=404,
            detail=f"Theme not found: {theme_id}. Available themes: {list(PRACTICE_DIALOGUES.keys())}"
        )

    # Find theme name
    theme_name = theme_id
    for theme in PRACTICE_THEMES:
        if theme.id == theme_id:
            theme_name = theme.name
            break

    dialogue = PRACTICE_DIALOGUES[theme_id]

    return PracticeDialogueResponse(
        theme_id=theme_id,
        theme_name=theme_name,
        dialogue=dialogue,
        word_count=count_dialogue_words(dialogue)
    )


@app.post("/upload-audio", response_model=UploadAudioResponse, tags=["Audio Processing"])
async def upload_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload audio file and start coaching analysis.

    **Authentication Required**: Bearer token from Supabase

    Steps:
    1. Generate coaching_id
    2. Save audio file locally
    3. Start background processing task
    4. Return coaching_id immediately

    Args:
        audio_file: Audio file (WAV, MP3, etc.)
        user: Authenticated user (from JWT token)

    Returns:
        Coaching ID and status
    """
    user_id = user["user_id"]
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
        background_tasks.add_task(process_audio_background, coaching_id,
                                audio_path)

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
async def get_coaching_status(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get coaching session status.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Status information
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    # Verify ownership
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")

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
async def get_coaching_metrics(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get overall speech metrics for a coaching session.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Speech metrics including score, pace, pitch, energy, pauses
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
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
async def get_detailed_metrics(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get detailed structured metrics with definitions and AI insights.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Full structured metrics JSON with ratings, definitions, and AI analysis
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    try:
        session_dir = storage_manager.get_session_directory(coaching_id)
        structured_metrics_path = os.path.join(session_dir, "output", "metrics", "structured_metrics.json")

        # Check if cached locally
        if os.path.exists(structured_metrics_path):
            with open(structured_metrics_path, 'r') as f:
                structured_metrics = json.load(f)
            return {
                "coaching_id": coaching_id,
                "metrics": structured_metrics
            }

        # Try to download from S3
        try:
            s3_key = f"{coaching_id}/output/metrics/structured_metrics.json"
            response = s3_client.get_object(
                Bucket=audio_processor.bucket_name,
                Key=s3_key
            )
            structured_metrics = json.loads(response['Body'].read())

            # Cache locally
            os.makedirs(os.path.dirname(structured_metrics_path), exist_ok=True)
            with open(structured_metrics_path, 'w') as f:
                json.dump(structured_metrics, f, indent=2)

            return {
                "coaching_id": coaching_id,
                "metrics": structured_metrics
            }
        except Exception as s3_error:
            print(f"Could not fetch from S3: {s3_error}")

        # Generate on-demand if not available
        print(f"Generating structured metrics on-demand for {coaching_id}")
        from services.metrics_generator import generate_structured_metrics

        analysis_path = metadata["analysis"]["analysis"]
        coaching_feedback_path = metadata["analysis"].get("coaching_feedback")

        structured_metrics = generate_structured_metrics(
            coaching_analysis_path=analysis_path,
            coaching_feedback_path=coaching_feedback_path if coaching_feedback_path and os.path.exists(coaching_feedback_path) else None
        )

        # Save and upload
        os.makedirs(os.path.dirname(structured_metrics_path), exist_ok=True)
        with open(structured_metrics_path, 'w') as f:
            json.dump(structured_metrics, f, indent=2)

        # Upload to S3
        s3_key = f"{coaching_id}/output/metrics/structured_metrics.json"
        audio_processor.upload_file_to_s3(structured_metrics_path, s3_key)

        return {
            "coaching_id": coaching_id,
            "metrics": structured_metrics
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading detailed metrics: {str(e)}")


@app.get("/coaching/{coaching_id}/feedback", response_model=CoachingFeedbackResponse, tags=["Coaching"])
async def get_coaching_feedback(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get detailed coaching feedback with segments.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Detailed feedback and segment analysis
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
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
async def get_visualization(
    coaching_id: str,
    viz_type: str,
    user: dict = Depends(get_current_user)
):
    """
    Get visualization file (SVG).

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        viz_type: Visualization type (pitch, intensity, spectrogram, etc.)
        user: Authenticated user (from JWT token)

    Returns:
        SVG file
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
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


@app.get("/coaching/{coaching_id}/waveform", tags=["Coaching"])
async def get_waveform(
    coaching_id: str,
    user: dict = Depends(get_current_user),
    samples: int = Query(1000, ge=100, le=5000, description="Number of waveform samples (100-5000)")
):
    """
    Get waveform visualization data with quality-coded segments.

    **Authentication Required**: Bearer token from Supabase

    Returns waveform peaks and color-coded segments based on speech quality.
    Segments are colored based on:
    - Green (#10b981): Normal speech
    - Orange (#f59e0b): Filler words or long pauses
    - Blue (#3b82f6): Low confidence words

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)
        samples: Number of waveform peaks to return (default: 1000)

    Returns:
        Waveform data with quality segments

    Example Response:
    {
      "duration_seconds": 18.5,
      "sample_rate": 44100,
      "waveform_data": {
        "peaks": [0.2, 0.5, 0.8, ...],
        "sample_count": 1000,
        "sample_interval_ms": 18.5
      },
      "quality_segments": [
        {
          "start_time": 0.0,
          "end_time": 3.2,
          "quality": "good",
          "color": "#10b981",
          "reason": "normal"
        }
      ]
    }
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    try:
        # Check if waveform data already cached
        session_dir = storage_manager.get_session_directory(coaching_id)
        waveform_cache_path = os.path.join(session_dir, "output", "waveform", f"waveform_{samples}.json")

        if os.path.exists(waveform_cache_path):
            # Return cached data
            with open(waveform_cache_path, 'r') as f:
                return json.load(f)

        # Generate waveform data
        audio_path = metadata.get("input", {}).get("wav_audio_file")
        analysis_path = metadata["analysis"]["analysis"]

        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")

        waveform_data = generate_waveform_data(
            audio_path=audio_path,
            coaching_analysis_path=analysis_path,
            target_samples=samples
        )

        # Cache the result
        os.makedirs(os.path.dirname(waveform_cache_path), exist_ok=True)
        with open(waveform_cache_path, 'w') as f:
            json.dump(waveform_data, f)

        return {
            "coaching_id": coaching_id,
            **waveform_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating waveform: {str(e)}")


@app.get("/coaching/{coaching_id}/transcript", response_model=TranscriptWithSegmentsResponse, tags=["Coaching"])
async def get_transcript_with_segments(
    coaching_id: str,
    user: dict = Depends(get_current_user),
    max_segments: int = Query(6, ge=1, le=10, description="Maximum number of segments to return")
):
    """
    Get interactive transcript with audio segments.

    **Authentication Required**: Bearer token from Supabase

    Selects interesting segments from the speech (issues or good examples) and
    provides both original and AI-improved audio for each segment.

    Segments are selected based on:
    - Filler words (um, uh, like, etc.)
    - Pace issues (too fast or too slow)
    - Low confidence transcription
    - Good examples of clear speech

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)
        max_segments: Maximum number of segments (default: 6, max: 10)

    Returns:
        List of segments with original and improved audio URLs

    Example Response:
    {
      "coaching_id": "coach_abc123",
      "segments": [
        {
          "segment_id": 1,
          "start_time": 2.5,
          "end_time": 7.8,
          "duration": 5.3,
          "text": "So um I think that we should like consider this option",
          "word_count": 10,
          "severity": "warning",
          "issues": [
            {
              "type": "filler-words",
              "description": "Contains 3 filler word(s)",
              "tip": "Try pausing instead of using filler words"
            }
          ],
          "original_audio_url": "https://s3.../segment_1.wav",
          "improved_audio_url": "https://s3.../segment_1_improved.wav"
        }
      ],
      "segment_count": 6
    }
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")

    if metadata.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Coaching analysis not yet completed")

    try:
        # Check if segments are already generated
        session_dir = storage_manager.get_session_directory(coaching_id)
        segments_cache_path = os.path.join(session_dir, "output", "segments", f"segments_{max_segments}.json")

        if os.path.exists(segments_cache_path):
            # Return cached segments
            with open(segments_cache_path, 'r') as f:
                cached_data = json.load(f)
                return TranscriptWithSegmentsResponse(
                    coaching_id=coaching_id,
                    segments=cached_data["segments"],
                    segment_count=len(cached_data["segments"])
                )

        # Generate segments
        audio_path = metadata.get("input", {}).get("wav_audio_file")
        analysis_path = metadata["analysis"]["analysis"]

        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")

        segments_output_dir = os.path.join(session_dir, "output", "segments")
        os.makedirs(segments_output_dir, exist_ok=True)

        # Get voice mapping from metadata (if voice cloning was performed)
        voice_mapping = metadata.get("voice_mapping")

        # Generate segments with audio
        segments = generate_segments_with_audio(
            audio_path=audio_path,
            coaching_analysis_path=analysis_path,
            output_dir=segments_output_dir,
            max_segments=max_segments,
            voice_mapping=voice_mapping
        )

        # Upload segment audio files to S3 and generate URLs
        for segment in segments:
            segment_id = segment['segment_id']

            # Upload original audio
            if segment.get('original_audio_path') and os.path.exists(segment['original_audio_path']):
                s3_key_original = f"{coaching_id}/segments/original/segment_{segment_id}.wav"
                with open(segment['original_audio_path'], 'rb') as f:
                    s3_client.put_object(
                        Bucket=audio_processor.bucket_name,
                        Key=s3_key_original,
                        Body=f
                    )
                # Generate presigned URL (valid for 24 hours)
                segment['original_audio_url'] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': audio_processor.bucket_name,
                        'Key': s3_key_original
                    },
                    ExpiresIn=86400  # 24 hours
                )

            # Upload improved audio
            if segment.get('improved_audio_path') and os.path.exists(segment['improved_audio_path']):
                s3_key_improved = f"{coaching_id}/segments/improved/segment_{segment_id}.wav"
                with open(segment['improved_audio_path'], 'rb') as f:
                    s3_client.put_object(
                        Bucket=audio_processor.bucket_name,
                        Key=s3_key_improved,
                        Body=f
                    )
                # Generate presigned URL (valid for 24 hours)
                segment['improved_audio_url'] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': audio_processor.bucket_name,
                        'Key': s3_key_improved
                    },
                    ExpiresIn=86400  # 24 hours
                )

            # Add duration field
            segment['duration'] = round(segment['end_time'] - segment['start_time'], 2)

        # Cache the segments
        cache_data = {
            "coaching_id": coaching_id,
            "segments": segments,
            "segment_count": len(segments)
        }
        with open(segments_cache_path, 'w') as f:
            json.dump(cache_data, f)

        return TranscriptWithSegmentsResponse(
            coaching_id=coaching_id,
            segments=segments,
            segment_count=len(segments)
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating segments: {str(e)}")


@app.get("/coaching/{coaching_id}/download", tags=["Coaching"])
async def download_all_results(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Download all results as a zip file.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Zip file with all results
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
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


@app.get("/coaching/{coaching_id}/full_original", tags=["Coaching"])
async def get_full_original(
    coaching_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get the full original audio recording for a coaching session.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)

    Returns:
        Original audio file
    """
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")

    # Check multiple possible locations for the audio file
    audio_path = metadata.get("input", {}).get("wav_audio_file")


    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Original audio file not found")

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=os.path.basename(audio_path)
    )


@app.delete("/coaching/{coaching_id}", tags=["Coaching"])
async def delete_coaching_session(
    coaching_id: str,
    user: dict = Depends(get_current_user),
    keep_s3: bool = Query(True)
):
    """
    Delete coaching session.

    **Authentication Required**: Bearer token from Supabase

    Args:
        coaching_id: Coaching session ID
        user: Authenticated user (from JWT token)
        keep_s3: Whether to keep S3 files (default: True)

    Returns:
        Deletion status
    """
    # Verify ownership
    metadata = storage_manager.load_session_metadata(coaching_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")
    if metadata.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: not your coaching session")
    metadata = storage_manager.load_session_metadata(coaching_id)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Coaching session not found: {coaching_id}")

    # Clean up local files
    storage_manager.cleanup_session(coaching_id, keep_metadata=False)

    # TODO: Optionally delete S3 files if keep_s3=False

    return {"message": f"Coaching session {coaching_id} deleted", "s3_files_kept": keep_s3}


@app.get("/sessions", tags=["Coaching"])
async def list_sessions(user: dict = Depends(get_current_user)):
    """
    List all coaching sessions for the authenticated user.
    Now fetches directly from Supabase database.

    **Authentication Required**: Bearer token from Supabase

    Args:
        user: Authenticated user (from JWT token)

    Returns:
        List of user's coaching sessions
    """
    user_id = user["user_id"]

    # Get sessions from database (already filtered by user_id and sorted)
    sessions = storage_manager.list_sessions_detailed(user_id=user_id)

    sessions_info = [
        {
            "coaching_id": session["coaching_id"],
            "status": session["status"],
            "created_at": session["created_at"],
            "completed_at": session.get("completed_at"),
            "audio_filename": session["audio_filename"]
        }
        for session in sessions
    ]

    return {"sessions": sessions_info, "count": len(sessions_info)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run SpeakRight Coaching API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--output-dir", type=str, help="Output directory for storing sessions (default: /tmp/speak-right or STORAGE_DIR env var)")

    args = parser.parse_args()

    # Reinitialize storage_manager if output-dir is provided
    if args.output_dir:
        storage_manager.base_dir = args.output_dir
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"Using output directory: {args.output_dir}")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
