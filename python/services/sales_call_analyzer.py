"""
Sales call analyzer — identifies speakers and produces
rep performance + customer behavior analysis from a transcript.
"""

from typing import Any, Dict, List, Optional

from utils.llm_client import call_llm

_SYSTEM = (
    "You are an expert sales coach and call analyst. "
    "Analyze sales call transcripts objectively and provide "
    "specific, actionable feedback."
)

_PROMPT = """\
Analyze this sales call transcript. The rep's lines and the \
customer's lines are provided separately.

REP TRANSCRIPT:
{rep_text}

CUSTOMER TRANSCRIPT:
{customer_text}

Return a JSON object with exactly these fields:
{{
  "overall_rep_score": <integer 0-100>,
  "communication_score": <integer 0-100>,
  "objection_handling_score": <integer 0-100>,
  "closing_score": <integer 0-100>,
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["area to improve 1", "area to improve 2"],
  "coaching_tips": [
    "specific actionable tip 1",
    "specific actionable tip 2"
  ],
  "key_moments": [
    {{
      "time": "mm:ss",
      "type": "objection_handled|missed_opportunity|strong_close|rapport_built",
      "note": "brief description"
    }}
  ],
  "lead_score": <integer 0-100>,
  "engagement_level": "<high|medium|low>",
  "customer_sentiment": "<positive|neutral|negative>",
  "customer_interests": ["interest 1", "interest 2"],
  "objections_raised": ["objection 1", "objection 2"],
  "buying_signals": ["signal 1", "signal 2"],
  "suggested_next_steps": ["step 1", "step 2"]
}}"""


class SalesCallAnalyzerService:
    def identify_speakers(
        self,
        transcript_data: Dict,
        rep_hint: Optional[str] = None) -> Dict[str, Any]:
        
        """
        Identify the sales rep speaker from a transcript.

        Heuristic: rep = speaker with the most words.
        All other speakers are treated as customers.

        Args:
            transcript_data: AWS Transcribe JSON dict
            rep_hint: Override speaker label, e.g. "spk_0"

        Returns:
            {
                "salesperson_label": "spk_0",
                "customer_labels": ["spk_1"]
            }
        """
        items = (
            transcript_data.get("results", {}).get("items", [])
        )

        word_counts: Dict[str, int] = {}
        for item in items:
            if item.get("type") != "pronunciation":
                continue
            label = item.get("speaker_label")
            if label:
                word_counts[label] = word_counts.get(label, 0) + 1

        all_labels = list(word_counts.keys())
        if not all_labels:
            return {
                "salesperson_label": "spk_0",
                "customer_labels": [],
            }

        if rep_hint and rep_hint in all_labels:
            rep = rep_hint
        else:
            rep = max(all_labels, key=lambda l: word_counts[l])

        customers = [l for l in all_labels if l != rep]
        return {
            "salesperson_label": rep,
            "customer_labels": customers,
        }

    def extract_speaker_turns(
        self,
        transcript_data: Dict,
        speaker_map: Dict[str, Any],
    ) -> Dict[str, List[Dict]]:
        """
        Split the transcript into rep turns and customer turns.

        Args:
            transcript_data: AWS Transcribe JSON dict
            speaker_map: Output of identify_speakers()

        Returns:
            {
                "rep_turns": [...],
                "customer_turns": [...],
                "full_transcript": [...]
            }
            Each turn: {speaker, role, start, end, text}
        """
        rep_label = speaker_map["salesperson_label"]
        customer_labels = set(speaker_map["customer_labels"])

        results = transcript_data.get("results", {})
        segments = (
            results.get("speaker_labels", {}).get("segments", [])
        )

        # Build start_time → content map from results.items
        # (speaker_labels segments don't carry alternatives/content)
        content_by_start: Dict[str, str] = {}
        for item in results.get("items", []):
            if item.get("type") != "pronunciation":
                continue
            st = item.get("start_time")
            alts = item.get("alternatives", [])
            if st and alts:
                content_by_start[st] = alts[0].get("content", "")

        rep_turns: List[Dict] = []
        customer_turns: List[Dict] = []
        full_transcript: List[Dict] = []

        for segment in segments:
            label = segment.get("speaker_label", "")
            start = float(segment.get("start_time", 0))
            end = float(segment.get("end_time", 0))

            words = [
                content_by_start[seg_item["start_time"]]
                for seg_item in segment.get("items", [])
                if seg_item.get("start_time") in content_by_start
            ]

            if not words:
                continue

            text = " ".join(words)

            if label == rep_label:
                role = "rep"
            elif label in customer_labels:
                role = "customer"
            else:
                role = "unknown"

            turn = {
                "speaker": label,
                "role": role,
                "start": start,
                "end": end,
                "text": text,
            }
            full_transcript.append(turn)

            if role == "rep":
                rep_turns.append(turn)
            elif role == "customer":
                customer_turns.append(turn)

        full_transcript.sort(key=lambda t: t["start"])

        return {
            "rep_turns": rep_turns,
            "customer_turns": customer_turns,
            "full_transcript": full_transcript,
        }

    def analyze_call(
        self,
        rep_turns: List[Dict],
        customer_turns: List[Dict],
    ) -> Dict:
        """
        Analyze a sales call from speaker-separated turns.

        Produces rep performance scores and customer behavior in
        a single LLM call. No external context required.

        Args:
            rep_turns: From extract_speaker_turns()["rep_turns"]
            customer_turns: From extract_speaker_turns()["customer_turns"]

        Returns:
            Analysis dict with rep scores + customer behavior fields.
        """
        rep_text = _turns_to_text(rep_turns)
        customer_text = _turns_to_text(customer_turns)

        prompt = _PROMPT.format(
            rep_text=rep_text or "(no rep speech detected)",
            customer_text=(
                customer_text or "(no customer speech detected)"
            ),
        )
        return call_llm(prompt, system=_SYSTEM, json_mode=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _turns_to_text(turns: List[Dict]) -> str:
    """Format turns as a timestamped transcript string.

    Input format:
        [
            {"speaker": "spk_0", "role": "rep",
             "start": 0.0, "end": 5.2, "text": "Hello, ..."},
            {"speaker": "spk_0", "role": "rep",
             "start": 8.1, "end": 12.4, "text": "We help ..."},
        ]

    Return format:
        "[00:00-00:05] Hello, ...\n[00:08-00:12] We help ..."
    """
    lines = []
    for turn in turns:
        start = turn.get("start", 0)
        end = turn.get("end", start)
        s_min, s_sec = int(start) // 60, int(start) % 60
        e_min, e_sec = int(end) // 60, int(end) % 60
        lines.append(
            f"[{s_min:02d}:{s_sec:02d}-{e_min:02d}:{e_sec:02d}]"
            f" {turn['text']}"
        )
    return "\n".join(lines)
