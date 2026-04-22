"""
Sales analyzer API endpoints.

Routes (mounted at /sales in main.py):
    POST /products                — create product + auto-generate script
    GET  /products                — list org products
    GET  /scripts/{id}            — get script detail
    POST /scripts/regenerate      — regenerate script for a product
    POST /calls/upload            — upload audio, start background analysis
    GET  /calls/{call_id}/status  — poll processing status
    GET  /calls/{call_id}/analysis — get completed analysis
    GET  /calls/{call_id}/export  — download transcript + meeting summary
    GET  /calls                   — list calls for current user
"""

import json
import logging
import os
import shutil
import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
)

from api.auth import get_current_user
from utils.aws_utils import s3_client
from api.database import SalesDatabaseService
from api.models import (
    CallAnalysisResponse,
    CallListItemResponse,
    CallStatusResponse,
    CallUpdateRequest,
    CallUpdateResponse,
    ProductCreateRequest,
    ProductResponse,
    RegenerateScriptRequest,
    ScriptResponse,
    SalesCallUploadResponse,
)
from services.sales_call_processor import SalesCallProcessorService
from services.script_generator import ScriptGeneratorService
from services.audio_processor import ensure_wav_format

logger = logging.getLogger(__name__)

sales_router = APIRouter(tags=["Sales"])

_db = SalesDatabaseService()
_script_gen = ScriptGeneratorService()
_processor = SalesCallProcessorService()

_UPLOAD_DIR = "/tmp/speak-right-sales"
_BUCKET = os.getenv("S3_BUCKET_NAME", "speach-analyzer")


@sales_router.post("/products", response_model=ProductResponse)
async def create_product(
    req: ProductCreateRequest,
    user: dict = Depends(get_current_user),
):
    """Create a product and auto-generate a sales script for it."""
    user_id = user["user_id"]
    org_id = _db.ensure_org(user_id)

    product = _db.add_row(table="products", data={
        "org_id": org_id,
        "created_by": user_id,
        "name": req.name,
        "description": req.description,
        "customer_profile": req.customer_profile,
        "talking_points": req.talking_points,
    })

    script_data = _script_gen.generate_script(
        name=req.name,
        description=req.description or "",
        customer_profile=req.customer_profile or "",
        talking_points=req.talking_points or "",
    )

    script = _db.add_row(table="sales_scripts", data={
        "org_id": org_id,
        "created_by": user_id,
        "product_id": product["id"],
        "title": f"{req.name} — Sales Script",
        "script_content": json.dumps(script_data),
        "key_phrases": script_data.get("key_phrases", []),
        "objection_handlers": script_data.get(
            "objection_handlers", {}
        ),
    })

    return ProductResponse(
        id=product["id"],
        name=product["name"],
        description=product.get("description"),
        customer_profile=product.get("customer_profile"),
        talking_points=product.get("talking_points"),
        script_id=script["id"],
        created_at=product.get("created_at"),
    )


@sales_router.get(
    "/products", response_model=list[ProductResponse]
)
async def list_products(
    user: dict = Depends(get_current_user),
    search: Optional[str] = Query(
        None, description="Filter across name, description, "
        "customer_profile, and talking_points"
    ),
    order_by: str = Query(
        "created_at", description="Column to sort by"
    ),
    order_desc: bool = Query(
        True, description="Sort descending if true"
    ),
):
    """List all products visible to the authenticated user's org."""
    products = _db.list_products(
        user_id=user["user_id"],
        search=search,
        order_by=order_by,
        order_desc=order_desc,
    )

    result = []
    for p in products:
        rows = _db.get_rows(
            table="sales_scripts",
            filters={"product_id": p["id"], "status": "active"},
            order_by="created_at",
            ascending=False,
            limit=1,
        )
        script = rows[0] if rows else None
        result.append(ProductResponse(
            id=p["id"],
            name=p["name"],
            description=p.get("description"),
            customer_profile=p.get("customer_profile"),
            talking_points=p.get("talking_points"),
            script_id=script["id"] if script else None,
            created_at=p.get("created_at"),
        ))

    return result


@sales_router.get(
    "/scripts/{script_id}", response_model=ScriptResponse
)
async def get_script(
    script_id: str,
    user: dict = Depends(get_current_user),
):
    """Fetch a sales script by ID."""
    rows = _db.get_rows(
        table="sales_scripts", filters={"id": script_id}
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail="Script not found"
        )
    return _format_script(rows[0])


@sales_router.post(
    "/scripts/regenerate", response_model=ScriptResponse
)
async def regenerate_script(
    req: RegenerateScriptRequest,
    user: dict = Depends(get_current_user),
):
    """Regenerate a sales script for an existing product."""
    user_id = user["user_id"]

    products = _db.list_products(user_id)
    product = next(
        (p for p in products if p["id"] == req.product_id), None
    )
    if not product:
        raise HTTPException(
            status_code=404, detail="Product not found"
        )

    script_data = _script_gen.generate_script(
        name=product["name"],
        description=product.get("description") or "",
        customer_profile=product.get("customer_profile") or "",
        talking_points=product.get("talking_points") or "",
    )

    title = f"{product['name']} — Sales Script"
    existing_rows = _db.get_rows(
        table="sales_scripts",
        filters={"product_id": product["id"], "status": "active"},
        order_by="created_at",
        ascending=False,
        limit=1,
    )
    script_payload = {
        "title": title,
        "script_content": json.dumps(script_data),
        "key_phrases": script_data.get("key_phrases", []),
        "objection_handlers": script_data.get(
            "objection_handlers", {}
        ),
    }

    if existing_rows:
        rows = _db.update_rows(
            table="sales_scripts",
            data=script_payload,
            filters={"id": existing_rows[0]["id"]},
        )
        script = rows[0]
    else:
        script = _db.add_row(table="sales_scripts", data={
            **script_payload,
            "org_id": product["org_id"],
            "created_by": user_id,
            "product_id": product["id"],
        })

    return _format_script(script)


@sales_router.post(
    "/calls/{call_id}/reanalyze",
    response_model=SalesCallUploadResponse,
)
async def reanalyze_sales_call(
    call_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Re-analyze an existing sales call."""
    try:
        background_tasks.add_task(
            _reprocess_call_background,
            call_id
        )
        return SalesCallUploadResponse(
            call_id=call_id, status="processing"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocessing call: {e}",
        )


@sales_router.post(
    "/calls/upload", response_model=SalesCallUploadResponse
)
async def upload_sales_call(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    rep_hint: Optional[str] = Query(
        None,
        description="Override speaker label for the rep "
        "(e.g. 'spk_0'). Defaults to speaker with most words.",
    ),
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]
    call_id = f"call_{uuid.uuid4().hex[:12]}"

    upload_dir = os.path.join(_UPLOAD_DIR, call_id)
    os.makedirs(upload_dir, exist_ok=True)

    audio_filename = audio_file.filename or "audio.wav"
    audio_path = os.path.join(upload_dir, audio_filename)

    try:
        with open(audio_path, "wb") as buf:
            shutil.copyfileobj(audio_file.file, buf)

        wav_path, _ = ensure_wav_format(audio_path)
        audio_filename = os.path.basename(wav_path)

        org_id = _db.ensure_org(user_id)
        _db.add_row(table="sales_calls", data={
            "org_id": org_id,
            "rep_id": user_id,
            "call_id": call_id,
            "audio_filename": audio_filename,
            "status": "pending",
        })

        background_tasks.add_task(
            _process_call_background,
            call_id,
            wav_path,
            user_id,
            rep_hint,
        )

        return SalesCallUploadResponse(
            call_id=call_id, status="pending"
        )

    except Exception as e:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading call: {e}",
        )


@sales_router.get(
    "/calls/{call_id}/status",
    response_model=CallStatusResponse,
)
async def get_call_status(
    call_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll the processing status of a sales call."""
    row = _fetch_call(call_id)
    if not row:
        raise HTTPException(
            status_code=404, detail="Call not found"
        )
    return CallStatusResponse(
        call_id=call_id,
        status=row["status"],
        error=row.get("error"),
    )


@sales_router.get(
    "/calls/{call_id}/analysis",
    response_model=CallAnalysisResponse,
)
async def get_call_analysis(
    call_id: str,
):
    """Get the full analysis for a completed sales call."""
    row = _fetch_call(call_id)
    if not row:
        raise HTTPException(
            status_code=404, detail="Call not found"
        )
    return CallAnalysisResponse(
        call_id=call_id,
        status=row["status"],
        error=row.get("error"),
        overall_rep_score=row.get("overall_rep_score"),
        communication_score=row.get("communication_score"),
        objection_handling_score=row.get(
            "objection_handling_score"
        ),
        closing_score=row.get("closing_score"),
        lead_score=row.get("lead_score"),
        engagement_level=row.get("engagement_level"),
        customer_sentiment=row.get("customer_sentiment"),
        rep_analysis=_parse_json_field(row.get("rep_analysis")),
        customer_analysis=_parse_json_field(
            row.get("customer_analysis")
        ),
        full_transcript=_parse_json_field(
            row.get("full_transcript")
        ),
        created_at=row.get("created_at"),
    )


@sales_router.get("/calls/{call_id}/audio")
async def get_call_audio(
    call_id: str,
    user: dict = Depends(get_current_user),
):
    """Return a pre-signed S3 URL for the original call audio."""
    row = _fetch_call(call_id)
    if not row:
        raise HTTPException(
            status_code=404, detail="Call not found"
        )

    audio_filename = row.get("audio_filename")
    if not audio_filename:
        raise HTTPException(
            status_code=404,
            detail="Audio file not found for this call",
        )

    s3_key = f"sales/{call_id}/audio/{audio_filename}"
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate audio URL: {e}",
        )

    return {"url": url}


@sales_router.get("/calls/{call_id}/export")
async def export_call(
    call_id: str,
    user: dict = Depends(get_current_user),
):
    """Download the transcript and meeting summary as a text file."""
    rows = _db.get_rows(
        table="sales_calls",
        filters={"call_id": call_id},
        select=(
            "audio_filename, created_at, duration_seconds, "
            "call_analyses(full_transcript, customer_analysis)"
        ),
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail="Call not found"
        )
    row = _merge_nested(rows[0], "call_analyses")
    txt = _build_txt_export(row, call_id)
    return Response(
        content=txt,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="speaknatural-{call_id}.txt"'
            )
        },
    )


@sales_router.get(
    "/calls", response_model=List[CallListItemResponse]
)
async def list_calls(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List sales calls for the current user, newest first."""
    rows = _db.get_rows(
        table="sales_calls",
        filters={"rep_id": user["user_id"]},
        select=(
            "*, call_analyses(overall_rep_score, lead_score,"
            " engagement_level, customer_sentiment)"
        ),
        order_by="created_at",
        ascending=False,
        limit=limit,
        offset=offset,
    )
    result = []
    for row in rows:
        _merge_nested(row, "call_analyses")
        result.append(CallListItemResponse(
            call_id=row["call_id"],
            status=row["status"],
            error=row.get("error"),
            audio_filename=row.get("audio_filename"),
            call_name=row.get("call_name"),
            created_at=row.get("created_at"),
            duration_seconds=row.get("duration_seconds"),
            overall_rep_score=row.get("overall_rep_score"),
            lead_score=row.get("lead_score"),
            engagement_level=row.get("engagement_level"),
            customer_sentiment=row.get("customer_sentiment"),
        ))
    return result


@sales_router.patch(
    "/calls/{call_id}", response_model=CallUpdateResponse
)
async def update_call(
    call_id: str,
    req: CallUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Rename a call. Only the owning rep can update."""
    name = req.call_name.strip()
    rows = _db.update_rows(
        table="sales_calls",
        data={"call_name": name},
        filters={"call_id": call_id, "rep_id": user["user_id"]},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Call not found")
    return CallUpdateResponse(call_id=call_id, call_name=name)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

def _process_call_background(
    call_id: str,
    audio_path: str,
    user_id: str,
    rep_hint: Optional[str],
) -> None:
    """Background task: run the full call processing pipeline."""
    try:
        _db.update_rows(
            table="sales_calls",
            data={"status": "processing"},
            filters={"call_id": call_id},
        )
        print(f"Started processing call {call_id} for user {user_id}")
        _processor.process_call(
            audio_file_path=audio_path,
            call_id=call_id,
            user_id=user_id,
            rep_hint=rep_hint,
        )
        print(f"Finished processing call {call_id}")
    except Exception as e:
        logger.error(
            "Call processing failed for %s: %s", call_id, e,
            exc_info=True,
        )
        _db.update_rows(
            table="sales_calls",
            data={"status": "failed", "error": str(e)},
            filters={"call_id": call_id},
        )


def _reprocess_call_background(
    call_id: str,
) -> None:
    """Background task: re-run analysis for an existing call."""
    try:
        _db.update_rows(
            table="sales_calls",
            data={"status": "processing"},
            filters={"call_id": call_id},
        )
        print(f"Started re-processing call {call_id}")
        _processor.reprocess_call(call_id=call_id)
        print(f"Finished re-processing call {call_id}")
    except Exception as e:
        logger.error(
            "Call re-processing failed for %s: %s", call_id, e,
            exc_info=True,
        )
        _db.update_rows(
            table="sales_calls",
            data={"status": "failed", "error": str(e)},
            filters={"call_id": call_id},
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_call(call_id: str) -> Optional[dict]:
    """Fetch a sales call merged with its analysis row."""
    rows = _db.get_rows(
        table="sales_calls",
        filters={"call_id": call_id},
        select=(
            "call_id, status, error, audio_filename, "
            "created_at, call_analyses(*)"
        ),
    )
    if not rows:
        return None
    return _merge_nested(rows[0], "call_analyses")




def _parse_json_field(value):
    """Parse a JSONB field that may be a string or already parsed."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def _build_txt_export(row: dict, call_id: str) -> str:
    filename = row.get("audio_filename", call_id)
    created = (row.get("created_at") or "")[:10]
    duration = row.get("duration_seconds")

    lines: List[str] = []
    dur_str = ""
    if duration:
        m, s = divmod(int(duration), 60)
        dur_str = f"   Duration: {m} min {s} sec"
    lines.append(f"MEETING TRANSCRIPT \u2014 {filename}")
    lines.append(f"Date: {created}{dur_str}")
    lines.append("\u2500" * 44)

    customer_analysis = _parse_json_field(
        row.get("customer_analysis")
    )
    if customer_analysis:
        lines.append("")
        lines.append("MEETING SUMMARY")
        for label, key, numbered in [
            ("Customer Interests", "customer_interests", False),
            ("Objections Raised", "objections_raised", False),
            ("Buying Signals", "buying_signals", False),
            ("Suggested Next Steps", "suggested_next_steps", True),
        ]:
            items = customer_analysis.get(key) or []
            if items:
                lines.append(f"  {label}:")
                for i, item in enumerate(items, 1):
                    prefix = f"{i}." if numbered else "\u2022"
                    lines.append(f"    {prefix} {item}")

    full_transcript = _parse_json_field(row.get("full_transcript"))
    if full_transcript:
        lines.append("")
        lines.append("FULL TRANSCRIPT")
        for turn in full_transcript:
            ts = _fmt_ts(float(turn.get("start", 0)))
            role = (turn.get("role") or "unknown").capitalize()
            lines.append(f"[{ts}] {role}: {turn.get('text', '')}")

    return "\n".join(lines)


def _merge_nested(row: dict, key: str) -> dict:
    # Supabase nested selects return the joined table as a list under
    # `key`. Pop it out and merge the first record into the parent row
    # so callers get a single flat dict.
    nested = row.pop(key, None) or []
    if nested:
        row.update(nested[0])
    return row


def _format_script(row: dict) -> ScriptResponse:
    """Parse a sales_scripts DB row into a ScriptResponse."""
    content = json.loads(row["script_content"])
    return ScriptResponse(
        id=row["id"],
        product_id=row.get("product_id"),
        title=row["title"],
        opening=content.get("opening", ""),
        discovery_questions=content.get(
            "discovery_questions", []
        ),
        value_propositions=content.get("value_propositions", []),
        objection_handlers=content.get("objection_handlers", {}),
        closing=content.get("closing", ""),
        key_phrases=content.get("key_phrases", []),
        created_at=row.get("created_at"),
    )
