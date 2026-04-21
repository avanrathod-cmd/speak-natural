"""
Sales call processor — orchestrates the full pipeline from
audio upload to stored analysis.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from api.database import SalesDatabaseService
from services.audio_processor import (
    AudioProcessorService,
    ensure_wav_format,
)
from services.sales_call_analyzer import SalesCallAnalyzerService

logger = logging.getLogger(__name__)

_BUCKET = os.getenv("S3_BUCKET_NAME", "speach-analyzer")


class SalesCallProcessorService:
    def __init__(self):
        self._audio = AudioProcessorService(bucket_name=_BUCKET)
        self._analyzer = SalesCallAnalyzerService()
        self._db = SalesDatabaseService()

    def process_call(
        self,
        audio_file_path: str,
        call_id: str,
        user_id: str,
        rep_hint: Optional[str] = None,
    ) -> Dict:
        """
        Full pipeline: WAV → S3 upload → transcription →
        speaker ID → analysis → save to DB.

        Args:
            audio_file_path: Local path to uploaded audio file
            call_id: Unique call identifier (e.g. "call_abc123")
            user_id: UUID of the uploading user
            rep_hint: Optional speaker label override (e.g. "spk_0")

        Returns:
            Analysis result dict
        """
        audio_filename = os.path.basename(audio_file_path)

        # 2. Upload audio to S3
        s3_key = f"sales/{call_id}/audio/{audio_filename}"
        s3_uri = self._audio.upload_audio_to_s3(audio_file_path, s3_key)
        logger.info("Uploaded audio to S3: %s", s3_uri)

        # 3. Transcribe (diarization already enabled)
        transcript = self._audio.transcribe_audio(s3_uri, call_id)
        logger.info("Transcription complete for call %s", call_id)

        # 4. Mark transcribed
        #self._db.update_rows(..., data={"status": "transcribed"}, ...)

        # 5. Identify speakers
        speaker_map = self._analyzer.identify_speakers(
            transcript, rep_hint
        )

        # 6. Extract turns
        turns = self._analyzer.extract_speaker_turns(
            transcript, speaker_map
        )

        # 7. Analyze
        analysis = self._analyzer.analyze_call(
            turns["rep_turns"], turns["customer_turns"]
        )
        logger.info("Analysis complete for call %s", call_id)

        # 8. Save to DB
        self._save_analysis(call_id, speaker_map, analysis, turns)

        # 9. Mark completed
        self._db.update_rows(
            table="sales_calls",
            data={
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"call_id": call_id},
        )

        return analysis

    def reprocess_call(
        self,
        call_id: str,
        rep_hint: Optional[str] = None,
    ) -> Dict:
        """
        Re-run analysis for an existing call (e.g. with new rep_hint).

        Args:
            call_id: Unique call identifier (e.g. "call_abc123")
            rep_hint: Optional speaker label override (e.g. "spk_0")

        Returns:
            Analysis result dict
        """
        # 1. Load existing transcript from DB
        rows = self._db.get_rows(
            table="sales_calls",
            filters={"call_id": call_id},
            select=(
                "call_id, status, error, audio_filename, "
                "created_at, call_analyses(*)"
            ),
        )
        if not rows:
            raise ValueError(
                f"No analysis found for call_id {call_id}"
            )
        row = rows[0]
        # Flatten nested call_analyses into the parent row
        analyses = row.pop("call_analyses", None) or []
        if analyses:
            row.update(analyses[0])

        full_transcript = row.get("full_transcript")
        logger.info(type(full_transcript))
        # check if full_transcript is empty or a string '[]'
        if not full_transcript or full_transcript in ("[]"):
            logger.info(
                "No transcript found for call_id %s, "
                "will attempt to re-transcribe from S3 audio.",
                call_id,
            )
            s3_key = (
                f"sales/{call_id}/audio/{row.get('audio_filename')}"
            )
            s3_uri = (
                f"s3://{self._audio.bucket_name}/{s3_key}"
            )
            full_transcript = self._audio.transcribe_audio(
                s3_uri, call_id
            )
            logger.info(
                "Re-transcription complete for call %s", call_id
            )

        # 2. Identify speakers
        speaker_map = self._analyzer.identify_speakers(
            full_transcript, rep_hint
        )

        # 3. Extract turns
        turns = self._analyzer.extract_speaker_turns(
            full_transcript, speaker_map
        )

        # 4. Analyze
        analysis = self._analyzer.analyze_call(
            turns["rep_turns"], turns["customer_turns"]
        )
        logger.info("Re-analysis complete for call %s", call_id)

        # 5. Update DB
        self._save_analysis(call_id, speaker_map, analysis, turns)
        return analysis

    def _save_analysis(
        self,
        call_id: str,
        speaker_map: Dict,
        analysis: Dict,
        turns: Dict,
    ) -> None:
        """Persist analysis results to call_analyses."""
        org_rows = self._db.get_rows(
            table="sales_calls",
            filters={"call_id": call_id},
            select="org_id",
        )
        if not org_rows:
            raise Exception(
                f"sales_calls row not found for call {call_id}"
            )
        org_id = org_rows[0]["org_id"]

        rep_analysis = {
            "strengths": analysis.get("strengths", []),
            "improvements": analysis.get("improvements", []),
            "coaching_tips": analysis.get("coaching_tips", []),
            "key_moments": analysis.get("key_moments", []),
        }
        customer_analysis = {
            "customer_interests": analysis.get(
                "customer_interests", []
            ),
            "objections_raised": analysis.get(
                "objections_raised", []
            ),
            "buying_signals": analysis.get("buying_signals", []),
            "suggested_next_steps": analysis.get(
                "suggested_next_steps", []
            ),
        }

        call_name = analysis.get("call_name")
        if call_name:
            # Only set if not already populated (e.g. from calendar event)
            self._db.update_rows(
                table="sales_calls",
                data={"call_name": call_name},
                filters={"call_id": call_id, "call_name": None},
            )

        self._db.add_row(table="call_analyses", data={
            "call_id": call_id,
            "org_id": org_id,
            "salesperson_speaker_label": speaker_map.get(
                "salesperson_label"
            ),
            "customer_speaker_labels": speaker_map.get(
                "customer_labels", []
            ),
            "overall_rep_score": analysis.get("overall_rep_score"),
            "communication_score": analysis.get(
                "communication_score"
            ),
            "objection_handling_score": analysis.get(
                "objection_handling_score"
            ),
            "closing_score": analysis.get("closing_score"),
            "rep_analysis": json.dumps(rep_analysis),
            "lead_score": analysis.get("lead_score"),
            "engagement_level": analysis.get("engagement_level"),
            "customer_sentiment": analysis.get("customer_sentiment"),
            "customer_analysis": json.dumps(customer_analysis),
            "full_transcript": json.dumps(
                turns["full_transcript"]
            ),
        })
