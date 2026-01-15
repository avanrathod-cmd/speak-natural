"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class UploadAudioResponse(BaseModel):
    """Response model for audio upload."""
    coaching_id: str = Field(..., description="Unique coaching session ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.now)


class CoachingStatusResponse(BaseModel):
    """Response model for coaching status."""
    coaching_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class MetricsResponse(BaseModel):
    """Response model for speech metrics."""
    coaching_id: str
    overall_score: float = Field(..., description="Overall score out of 10")
    pace_wpm: float = Field(..., description="Speaking pace in words per minute")
    pitch_variation: str = Field(..., description="Pitch variation rating")
    energy_level: str = Field(..., description="Energy level rating")
    pause_distribution: Dict = Field(..., description="Pause distribution stats")


class SegmentResponse(BaseModel):
    """Response model for audio segment."""
    segment_id: int
    start_time: float
    end_time: float
    duration: float
    transcript: str
    original_audio_url: Optional[str] = None
    improved_audio_url: Optional[str] = None
    feedback: Optional[str] = None


class CoachingFeedbackResponse(BaseModel):
    """Response model for detailed coaching feedback."""
    coaching_id: str
    general_feedback: str
    strong_points: List[str]
    improvements: List[str]
    segments: List[SegmentResponse]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    coaching_id: Optional[str] = None


class SignupRequest(BaseModel):
    """Mock signup request."""
    email: str
    password: str
    name: Optional[str] = None


class SignupResponse(BaseModel):
    """Mock signup response."""
    user_id: str
    email: str
    token: str
    message: str
