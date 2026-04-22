import os
from deepgram import DeepgramClient, PrerecordedOptions, UrlSource
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

_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY", ""))


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
    options = PrerecordedOptions(
        model="nova-3",
        language="multi",
        diarize=True,
        utterances=True,
        punctuate=True,
    )
    response = _client.listen.rest.v("1").transcribe_url(
        UrlSource(url=url), options
    )
    return _normalize(response)


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    without_scheme = s3_uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


def _normalize(response) -> Transcript:
    words = response.results.channels[0].alternatives[0].words
    items = [
        TranscriptItem(
            type="pronunciation",
            speaker_label=f"spk_{w.speaker}",
            start_time=str(w.start),
            end_time=str(w.end),
            alternatives=[TranscriptAlternative(
                content=w.word,
                confidence=str(w.confidence),
            )],
        )
        for w in words
    ]
    segments = [
        SpeakerSegment(
            speaker_label=f"spk_{u.speaker}",
            start_time=str(u.start),
            end_time=str(u.end),
            items=[SegmentItem(start_time=str(w.start)) for w in u.words],
        )
        for u in response.results.utterances
    ]
    return Transcript(
        results=TranscriptResults(
            items=items,
            speaker_labels=SpeakerLabels(segments=segments),
        )
    )