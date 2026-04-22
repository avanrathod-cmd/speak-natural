import os
from deepgram import DeepgramClient
from utils.aws_utils import s3_client
from models.transcript import (
    Transcript,
    TranscriptResults,
    TranscriptItem,
    TranscriptAlternative,
    SpeakerLabels,
    SpeakerSegment,
    SegmentItem,
)

_PRESIGN_EXPIRY = 600  # seconds

_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY", ""))


def transcribe_from_s3(s3_uri: str) -> Transcript:
    """
    Transcribe audio stored in S3 using Deepgram Nova-3 Multilingual.

    Generates a pre-signed URL from the S3 URI and sends it to
    Deepgram — no re-download of the audio file required.
    Returns a typed Transcript ready for SalesCallAnalyzerService.
    """
    bucket, key = _parse_s3_uri(s3_uri)
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PRESIGN_EXPIRY,
    )
    response = _client.listen.v1.media.transcribe_url(
        url=url,
        model="nova-3",
        language="multi",
        diarize=True,
        utterances=True,
        punctuate=True,
    )
    return _normalize(response)


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    without_scheme = s3_uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


def _normalize(response) -> Transcript:
    # Utterance words carry speaker labels; channel words do not.
    # Build both items and segments from utterances so speaker info
    # is always present.
    utterances = response.results.utterances or []
    items = [
        TranscriptItem(
            type="pronunciation",
            speaker_label=f"spk_{w.speaker}",
            start_time=str(w.start),
            end_time=str(w.end),
            alternatives=[TranscriptAlternative(
                content=w.word or "",
                confidence=str(w.confidence or 0),
            )],
        )
        for u in utterances
        for w in (u.words or [])
        if w.word
    ]
    segments = [
        SpeakerSegment(
            speaker_label=f"spk_{u.speaker}",
            start_time=str(u.start),
            end_time=str(u.end),
            items=[
                SegmentItem(start_time=str(w.start))
                for w in (u.words or [])
                if w.word
            ],
        )
        for u in utterances
    ]
    return Transcript(
        results=TranscriptResults(
            items=items,
            speaker_labels=SpeakerLabels(segments=segments),
        )
    )