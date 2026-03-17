"""
Sales call processor — orchestrates the full pipeline from
audio upload to stored analysis.
"""

import logging
import os
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
        #logger.info("Transcript: %s", transcript)

        # 4. Mark transcribed
        #self._db.update_sales_call_status(call_id, "transcribed")

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
        self._db.save_call_analysis(
            call_id=call_id,
            speaker_map=speaker_map,
            analysis=analysis,
            full_transcript=turns["full_transcript"],
        )

        # 9. Mark completed
        self._db.update_sales_call_status(call_id, "completed")

        return analysis
    
    def reprocess_call(
        self,
        call_id: str,
        #user_id: str,
        rep_hint: Optional[str] = None,
    ) -> Dict:
        """
        Re-run analysis for an existing call (e.g. with new rep_hint).

        Args:
            call_id: Unique call identifier (e.g. "call_abc123")
            user_id: UUID of the uploading user
            rep_hint: Optional speaker label override (e.g. "spk_0")

        Returns:
            Analysis result dict
        """
        # 1. Load existing transcript from DB
        row = self._db.get_call_analysis(call_id)
        if not row:
            raise ValueError(f"No analysis found for call_id {call_id}")
        
        full_transcript = row.get("full_transcript")
        logger.info(type(full_transcript))
        #check is full_script is a string of the form '[]'
        if not full_transcript or full_transcript in ("[]"):
            print(f"""No transcript found for call_id {call_id},
                    will attempt to re-transcribe from S3 audio.""")
            s3_key = f"sales/{call_id}/audio/{row.get('audio_filename')}"
            s3_uri = f"s3://{self._audio.bucket_name}/{s3_key}"
            full_transcript = self._audio.transcribe_audio(s3_uri, call_id)
            print(f"Re-transcription complete for call {call_id}")

        # 2. Identify speakers
        speaker_map = self._analyzer.identify_speakers(full_transcript, rep_hint)
        
        # 3. Extract turns
        turns = self._analyzer.extract_speaker_turns(full_transcript, speaker_map)
        
        # 4. Analyze
        analysis = self._analyzer.analyze_call(
            turns["rep_turns"], turns["customer_turns"]
        )
        logger.info("Re-analysis complete for call %s", call_id)
        # 5. Update DB
        self._db.save_call_analysis(
            call_id=call_id,
            speaker_map=speaker_map,
            analysis=analysis,
            full_transcript=turns["full_transcript"],
        )
        return analysis
            
