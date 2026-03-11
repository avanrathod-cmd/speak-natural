"""
Shared LLM client for sales analyzer.

Provider and model are read from .env:
    LLM_PROVIDER=gemini          (default)
    LLM_MODEL=gemini-2.0-flash   (default)
    GOOGLE_API_KEY=...

Switching providers only requires changing env vars — no code changes in service files.
"""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
_LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")


def call_llm(prompt: str, system: str = "", json_mode: bool = True) -> Any:
    """
    Call the configured LLM provider.

    Args:
        prompt: User message / main prompt.
        system: Optional system prompt.
        json_mode: When True, instructs the model to return valid JSON
                   and parses the response before returning.

    Returns:
        Parsed dict/list when json_mode=True, otherwise raw text string.
    """
    if _LLM_PROVIDER == "gemini":
        return _call_gemini(prompt, system, json_mode)
    elif _LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt, system, json_mode)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {_LLM_PROVIDER!r}. Set LLM_PROVIDER=gemini or anthropic in .env.")


def _call_gemini(prompt: str, system: str, json_mode: bool) -> Any:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)

    config_kwargs: dict = {}
    if system:
        config_kwargs["system_instruction"] = system
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=_LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
    )

    text = response.text
    if json_mode:
        raw = re.sub(r"^```(?:json)?\s*", "", text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    return text


def _call_anthropic(prompt: str, system: str, json_mode: bool) -> Any:
    from anthropic import Anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = Anthropic(api_key=api_key)

    system_prompt = system
    if json_mode:
        json_instruction = "Respond with valid JSON only. Do not include any text outside the JSON."
        system_prompt = f"{system_prompt}\n\n{json_instruction}".strip() if system_prompt else json_instruction

    messages = [{"role": "user", "content": prompt}]
    if json_mode:
        messages.append({"role": "assistant", "content": "{"})

    response = client.messages.create(
        model=_LLM_MODEL,
        max_tokens=4096,
        system=system_prompt or None,
        messages=messages,
    )

    text = response.content[0].text
    if json_mode:
        raw = "{" + text
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    return text
