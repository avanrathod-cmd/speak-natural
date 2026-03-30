"""
Guest (unauthenticated) sales call analysis endpoints.

Routes (mounted at /sales in main.py):
    POST   /guest/calls/upload            — upload audio, enqueue background
                                            task, return {job_id}
    GET    /guest/calls/{job_id}/status   — poll processing status
    GET    /guest/calls/{job_id}/analysis — fetch completed analysis
    DELETE /guest/calls/{job_id}          — delete S3 object + remove job entry

No DB writes at any point. S3 is used as transient scratch space only:
the audio object is deleted immediately after transcription completes.
Job state lives in a module-level dict — safe for single-worker deployments.
"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from services.audio_processor import AudioProcessorService, ensure_wav_format
from services.sales_call_analyzer import SalesCallAnalyzerService
from utils.aws_utils import s3_client

logger = logging.getLogger(__name__)

guest_router = APIRouter(tags=["Guest"])

# ---------------------------------------------------------------------------
# Module-level job store
# {job_id: {status, s3_key, result, error, created_at}}
# ---------------------------------------------------------------------------
_jobs: dict[str, dict] = {}

_BUCKET = os.getenv("S3_BUCKET_NAME", "speach-analyzer")
_MAX_UPLOAD_MB = int(os.getenv("GUEST_MAX_UPLOAD_MB", "50"))
_UPLOAD_DIR = "/tmp/speak-right-guest"

_audio_svc = AudioProcessorService(bucket_name=_BUCKET)
_analyzer = SalesCallAnalyzerService()


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@guest_router.post("/guest/calls/upload")
async def upload_guest_call(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    rep_hint: Optional[str] = Query(
        None,
        description="Override speaker label for the rep (e.g. 'spk_0'). "
        "Defaults to speaker with most words.",
    ),
):
    """Upload a call audio file and start background analysis."""
    job_id = f"guest_{uuid.uuid4().hex[:12]}"

    upload_dir = os.path.join(_UPLOAD_DIR, job_id)
    os.makedirs(upload_dir, exist_ok=True)

    audio_filename = audio_file.filename or "audio.wav"
    audio_path = os.path.join(upload_dir, audio_filename)

    try:
        contents = await audio_file.read()
        if len(contents) > _MAX_UPLOAD_MB * 1024 * 1024:
            shutil.rmtree(upload_dir, ignore_errors=True)
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {_MAX_UPLOAD_MB} MB limit.",
            )
        with open(audio_path, "wb") as f:
            f.write(contents)

        wav_path, _ = ensure_wav_format(audio_path)

        _jobs[job_id] = {
            "status": "pending",
            "s3_key": None,
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        background_tasks.add_task(
            _process_guest_call,
            job_id,
            wav_path,
            rep_hint,
        )

        return {"job_id": job_id, "status": "pending"}

    except HTTPException:
        raise
    except Exception as e:
        shutil.rmtree(upload_dir, ignore_errors=True)
        _jobs.pop(job_id, None)
        raise HTTPException(
            status_code=500, detail=f"Upload failed: {e}"
        )


@guest_router.get("/guest/calls/{job_id}/status")
async def get_guest_call_status(job_id: str):
    """Poll the processing status of a guest analysis job."""
    job = _get_job_or_404(job_id)
    return {
        "job_id": job_id,
        "status": job["status"],
        "error": job.get("error"),
    }


@guest_router.get("/guest/calls/{job_id}/analysis")
async def get_guest_call_analysis(job_id: str):
    """Fetch the completed analysis for a guest job."""
    job = _get_job_or_404(job_id)
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status: {job['status']}).",
        )
    return job["result"]


@guest_router.delete("/guest/calls/{job_id}")
async def delete_guest_call(job_id: str):
    """
    Clean up a guest job: delete the S3 audio object (if present)
    and remove the job store entry.
    """
    job = _get_job_or_404(job_id)

    s3_key = job.get("s3_key")
    if s3_key:
        try:
            s3_client.delete_object(Bucket=_BUCKET, Key=s3_key)
        except Exception as e:
            logger.warning(
                "Could not delete S3 object %s: %s", s3_key, e
            )

    _jobs.pop(job_id, None)
    return {"job_id": job_id, "deleted": True}


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def _process_guest_call(
    job_id: str,
    wav_path: str,
    rep_hint: Optional[str],
) -> None:
    """
    Full guest pipeline:
    WAV → S3 upload → transcribe → delete S3 → speaker ID →
    turn extraction → LLM analysis → store in job dict → /tmp cleanup.
    """
    upload_dir = os.path.dirname(wav_path)
    audio_filename = os.path.basename(wav_path)
    s3_key = f"guest/{job_id}/audio/{audio_filename}"

    try:
        _jobs[job_id]["status"] = "transcribing"

        s3_uri = _audio_svc.upload_audio_to_s3(wav_path, s3_key)
        _jobs[job_id]["s3_key"] = s3_key
        logger.info("Guest %s: uploaded to S3 %s", job_id, s3_uri)

        transcript = _audio_svc.transcribe_audio(s3_uri, job_id)
        logger.info("Guest %s: transcription complete", job_id)

    except Exception as e:
        logger.error(
            "Guest %s: transcription failed: %s", job_id, e,
            exc_info=True,
        )
        _jobs[job_id].update({"status": "failed", "error": str(e)})
        return
    finally:
        # Always attempt S3 cleanup after transcription
        try:
            s3_client.delete_object(Bucket=_BUCKET, Key=s3_key)
            _jobs[job_id]["s3_key"] = None
            logger.info("Guest %s: S3 object deleted", job_id)
        except Exception as e:
            logger.warning(
                "Guest %s: could not delete S3 object: %s", job_id, e
            )
        shutil.rmtree(upload_dir, ignore_errors=True)

    try:
        _jobs[job_id]["status"] = "analyzing"

        speaker_map = _analyzer.identify_speakers(transcript, rep_hint)
        turns = _analyzer.extract_speaker_turns(transcript, speaker_map)
        analysis = _analyzer.analyze_call(
            turns["rep_turns"], turns["customer_turns"]
        )

        _jobs[job_id].update({"status": "completed", "result": analysis})
        logger.info("Guest %s: analysis complete", job_id)

    except Exception as e:
        logger.error(
            "Guest %s: analysis failed: %s", job_id, e, exc_info=True
        )
        _jobs[job_id].update({"status": "failed", "error": str(e)})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_job_or_404(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
