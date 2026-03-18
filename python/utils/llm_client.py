"""
Shared LLM client for sales analyzer.

Provider and model are read from .env:
    LLM_PROVIDER=gemini          (default)
    LLM_MODEL=gemini-2.0-flash   (default)
    GOOGLE_API_KEY=...

Switching providers only requires changing env vars — no code changes in service files.
"""

import json
import logging
import os
import re
import time
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
_LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
_LLM_MAX_RETRIES = 3
_LLM_RETRY_DELAY = 1.0


def _retry_with_backoff(func, max_retries: int = _LLM_MAX_RETRIES,
                        initial_delay: float = _LLM_RETRY_DELAY):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Callable that may raise an exception.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds (doubles each retry).
    
    Returns:
        Result of the function call.
    
    Raises:
        The last exception if all retries fail.
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    str(e),
                )
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(
                    "LLM call failed after %d attempts: %s",
                    max_retries + 1,
                    str(e),
                )
    
    if last_exception:
        raise last_exception


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
    print(f"prompt = {prompt}   system = {system}   json_mode = {json_mode} ")
    response = None
    if _LLM_PROVIDER == "gemini":
        response = _call_gemini(prompt, system, json_mode)
    elif _LLM_PROVIDER == "anthropic":
        response = _call_anthropic(prompt, system, json_mode)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {_LLM_PROVIDER!r}. Set LLM_PROVIDER=gemini or anthropic in .env.")

    print(f"response = {response}")
    return response

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

    def _make_request():
        return client.models.generate_content(
            model=_LLM_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
        )

    try:
        response = _retry_with_backoff(_make_request)
    except Exception as e:
        logger.error("Error occurred while calling Gemini: %s", e)
        raise

    text = response.text
    if json_mode:
        raw = re.sub(r"^```(?:json)?\s*", "", text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]
        return parsed

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

    def _make_request():
        return client.messages.create(
            model=_LLM_MODEL,
            max_tokens=4096,
            system=system_prompt or None,
            messages=messages,
        )

    try:
        response = _retry_with_backoff(_make_request)
    except Exception as e:
        logger.error("Error occurred while calling Anthropic: %s", e)
        raise

    text = response.content[0].text
    if json_mode:
        raw = "{" + text
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    return text
