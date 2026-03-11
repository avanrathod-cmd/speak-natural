"""
Script generator service — creates structured sales scripts
from product context using LLM.
"""

from utils.llm_client import call_llm

_SYSTEM = (
    "You are an expert sales coach. Generate structured, practical "
    "sales scripts based on product and customer context. "
    "Be specific and actionable."
)

_PROMPT = """\
Generate a sales script for the following product:

Product Name: {name}
Description: {description}
Target Customer Profile: {customer_profile}
Key Talking Points: {talking_points}

Return a JSON object with exactly these fields:
{{
  "opening": "Opening hook (2-3 sentences)",
  "discovery_questions": [
    "question 1", "question 2", "question 3",
    "question 4", "question 5"
  ],
  "value_propositions": [
    "value prop 1", "value prop 2", "value prop 3"
  ],
  "objection_handlers": {{
    "objection 1": "response 1",
    "objection 2": "response 2",
    "objection 3": "response 3"
  }},
  "closing": "Closing statement / call to action (2-3 sentences)",
  "key_phrases": [
    "must-say phrase 1",
    "must-say phrase 2",
    "must-say phrase 3"
  ]
}}"""


class ScriptGeneratorService:
    def generate_script(
        self,
        name: str,
        description: str,
        customer_profile: str,
        talking_points: str,
    ) -> dict:
        """
        Generate a structured sales script for the given product.

        Returns a dict with keys: opening, discovery_questions,
        value_propositions, objection_handlers, closing, key_phrases.
        """
        prompt = _PROMPT.format(
            name=name,
            description=description or "Not specified",
            customer_profile=customer_profile or "Not specified",
            talking_points=talking_points or "Not specified",
        )
        return call_llm(prompt, system=_SYSTEM, json_mode=True)
