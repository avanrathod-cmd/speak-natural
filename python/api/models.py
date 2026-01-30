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
    original_ssml: str = Field(..., description="Segment transcript ssml text"),
    improved_ssml: str = Field(..., description="Improved segment transcript text"),
    severity: str = Field(..., description="Severity: good, warning, or error")
    severity_score: float
    quality_score: float
    is_exemplary: bool
    primary_issue: Optional[Dict] = None
    original_audio_url: Optional[str] = None
    improved_audio_url: Optional[str] = None


class TranscriptWithSegmentsResponse(BaseModel):
    """Response model for interactive transcript with audio segments."""
    coaching_id: str
    segments: List[SegmentResponse] = Field(..., description="Selected interesting segments with audio")
    segment_count: int


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


class PracticeTheme(BaseModel):
    """Model for a practice theme."""
    id: str = Field(..., description="Unique theme identifier")
    name: str = Field(..., description="Display name of the theme")
    description: str = Field(..., description="Brief description of the theme")
    icon: str = Field(..., description="Icon identifier (MessageSquare, TrendingUp, PlayCircle)")


class PracticeThemesResponse(BaseModel):
    """Response model for list of practice themes."""
    themes: List[PracticeTheme] = Field(..., description="List of available practice themes")


class PracticeDialogueResponse(BaseModel):
    """Response model for a practice dialogue."""
    theme_id: str = Field(..., description="Theme identifier")
    theme_name: str = Field(..., description="Theme display name")
    dialogue: str = Field(..., description="Dialogue text with **bold** markers for emphasis")
    word_count: int = Field(..., description="Approximate word count")


# Practice Analysis Models

class WordBreakdown(BaseModel):
    """Per-word analysis breakdown for practice scoring."""
    word: str = Field(..., description="The word analyzed")
    expected_emphasis: str = Field(..., description="Expected emphasis: none, moderate, or strong")
    energy_relative: float = Field(..., description="Ratio of word energy to user's baseline")
    emphasis_score: float = Field(..., ge=0, le=100, description="Score for emphasis delivery")
    expected_pause_ms: int = Field(..., description="Expected pause after word in ms")
    actual_pause_ms: float = Field(..., description="Actual pause after word in ms")
    pause_score: float = Field(..., ge=0, le=100, description="Score for pause timing")


class BaselineStats(BaseModel):
    """User's baseline statistics computed from their recording."""
    energy_mean_db: float = Field(..., description="Mean energy in dB")
    pitch_mean_hz: float = Field(..., description="Mean pitch in Hz")
    duration_seconds: float = Field(..., description="Total recording duration")


class PracticeAnalyzeResponse(BaseModel):
    """Response model for practice segment analysis."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall practice score (0-100)")
    emphasis_score: int = Field(..., ge=0, le=100, description="Score for word emphasis (40% weight)")
    pause_score: int = Field(..., ge=0, le=100, description="Score for pause timing (30% weight)")
    pitch_score: int = Field(..., ge=0, le=100, description="Score for pitch variation (20% weight)")
    speed_score: int = Field(..., ge=0, le=100, description="Score for pace matching (10% weight)")
    passed: bool = Field(..., description="True if overall_score >= 80 (mastered)")
    word_breakdown: List[WordBreakdown] = Field(..., description="Per-word analysis details")
    baseline: BaselineStats = Field(..., description="User's computed baseline for this recording")
