from __future__ import annotations

import os
from threading import Lock

from dotenv import load_dotenv
from openai import OpenAI


class OpenAIClientError(RuntimeError):
    """Base error for lazy OpenAI client initialization."""


class OpenAIConfigurationError(OpenAIClientError):
    """Raised when the OpenAI client is requested without required config."""


class OpenAIInitializationError(OpenAIClientError):
    """Raised when the OpenAI client cannot be constructed."""


_openai_client = None
_openai_client_lock = Lock()


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    load_dotenv()
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise OpenAIConfigurationError(
            "OPENAI_API_KEY is not set. AI features require a configured OpenAI API key."
        )

    with _openai_client_lock:
        if _openai_client is None:
            try:
                _openai_client = OpenAI(api_key=api_key)
            except Exception as exc:
                raise OpenAIInitializationError(
                    "Failed to initialize the OpenAI client. Check OpenAI configuration and dependencies."
                ) from exc
    return _openai_client


def reset_openai_client() -> None:
    global _openai_client
    with _openai_client_lock:
        _openai_client = None


def call_openai(messages, model: str = "gpt-4o", **kwargs):
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    return {
        "content": response.choices[0].message.content,
        "usage": response.usage,
        "model": model,
    }
