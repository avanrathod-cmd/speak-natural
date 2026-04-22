"""
Internal transcript models.

Represents the normalized transcript format produced by the
transcription layer and consumed by SalesCallAnalyzerService.
"""
from pydantic import BaseModel
from typing import List


class TranscriptAlternative(BaseModel):
    """Word text and confidence score for a single recognition result."""
    content: str
    confidence: str


class TranscriptItem(BaseModel):
    """A single spoken word with timing, speaker, and recognition data."""
    type: str           # always "pronunciation" (punctuation tokens omitted)
    speaker_label: str  # e.g. "spk_0"
    start_time: str     # seconds as string, e.g. "0.500"
    end_time: str
    alternatives: List[TranscriptAlternative]


class SegmentItem(BaseModel):
    """Back-reference from a speaker segment to a word by start time."""
    start_time: str


class SpeakerSegment(BaseModel):
    """A contiguous block of speech by one speaker (utterance boundary)."""
    speaker_label: str
    start_time: str
    end_time: str
    items: List[SegmentItem]  # start_times of words in this segment


class SpeakerLabels(BaseModel):
    """All speaker segments in the call."""
    segments: List[SpeakerSegment]


class TranscriptResults(BaseModel):
    """Top-level results container."""
    items: List[TranscriptItem]
    speaker_labels: SpeakerLabels


class Transcript(BaseModel):
    """Normalized transcript returned by the transcription layer."""
    results: TranscriptResults