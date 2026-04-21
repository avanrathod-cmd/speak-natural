"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# ---------------------------------------------------------------------------
# Sales Analyzer models
# ---------------------------------------------------------------------------

class ProductCreateRequest(BaseModel):
    """Request model for creating a product."""
    name: str
    description: Optional[str] = None
    customer_profile: Optional[str] = None
    talking_points: Optional[str] = None


class ProductResponse(BaseModel):
    """Response model for a product."""
    id: str
    name: str
    description: Optional[str] = None
    customer_profile: Optional[str] = None
    talking_points: Optional[str] = None
    script_id: Optional[str] = None
    created_at: Optional[datetime] = None


class ScriptResponse(BaseModel):
    """Response model for a generated sales script."""
    id: str
    product_id: Optional[str] = None
    title: str
    opening: str
    discovery_questions: List[str]
    value_propositions: List[str]
    objection_handlers: Dict[str, str]
    closing: str
    key_phrases: List[str]
    created_at: Optional[datetime] = None


class RegenerateScriptRequest(BaseModel):
    """Request model for regenerating a script."""
    product_id: str


class SalesCallUploadResponse(BaseModel):
    """Response model for a sales call upload."""
    call_id: str
    status: str  # "pending"


class CallStatusResponse(BaseModel):
    """Response model for sales call processing status."""
    call_id: str
    status: str  # pending/processing/transcribed/completed/failed
    error: Optional[str] = None


class CallAnalysisResponse(BaseModel):
    """Response model for a completed sales call analysis."""
    call_id: str
    status: str
    error: Optional[str] = None
    overall_rep_score: Optional[int] = None
    communication_score: Optional[int] = None
    objection_handling_score: Optional[int] = None
    closing_score: Optional[int] = None
    lead_score: Optional[int] = None
    engagement_level: Optional[str] = None
    customer_sentiment: Optional[str] = None
    rep_analysis: Optional[Dict] = None
    customer_analysis: Optional[Dict] = None
    full_transcript: Optional[List] = None
    created_at: Optional[datetime] = None


class CallListItemResponse(BaseModel):
    """Response model for a sales call in list view."""
    call_id: str
    status: str
    error: Optional[str] = None
    audio_filename: Optional[str] = None
    call_name: Optional[str] = None
    created_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    overall_rep_score: Optional[int] = None
    lead_score: Optional[int] = None
    engagement_level: Optional[str] = None
    customer_sentiment: Optional[str] = None


class CallUpdateRequest(BaseModel):
    call_name: str = Field(..., max_length=100)


class CallUpdateResponse(BaseModel):
    call_id: str
    call_name: str

