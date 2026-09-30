"""Invoke a local Ollama model with structured output."""

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request
from urllib.request import urlopen


DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
DEFAULT_TIMEOUT_SECONDS = 120.0
INVESTIGATION_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "ai-investigation.schema.json"
)


def load_investigation_schema() -> dict[str, Any]:
    """Load the canonical AI investigation response schema."""
    with INVESTIGATION_SCHEMA_PATH.open(
        encoding="utf-8"
    ) as schema_file:
        return json.load(schema_file)


def require_local_endpoint(endpoint: str) -> str:
    """Reject endpoints that could send evidence off the host."""
    parsed_endpoint = urlparse(endpoint)

    if (
        parsed_endpoint.scheme != "http"
        or parsed_endpoint.hostname
        not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }
    ):
        raise ValueError(
            "Ollama endpoint must use local HTTP"
        )

    return endpoint


def invoke_ollama(
    prompt: str,
    system_prompt: str,
    model_id: str,
    endpoint: str = DEFAULT_OLLAMA_ENDPOINT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    transport: Any | None = None,
) -> dict[str, Any]:
    """Invoke Ollama without sending evidence off the host."""
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError(
            "Ollama model_id must be a non-empty string"
        )

    require_local_endpoint(endpoint)

    payload = {
        "model": model_id.strip(),
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "think": False,
        "format": load_investigation_schema(),
        "options": {
            "temperature": 0,
            "num_predict": 700,
        },
    }

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    open_request = transport or urlopen

    try:
        with open_request(
            request,
            timeout=timeout_seconds,
        ) as response:
            response_body = response.read().decode(
                "utf-8"
            )
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(
            "Local Ollama request failed"
        ) from error

    try:
        ollama_response = json.loads(response_body)
        response_text = ollama_response[
            "message"
        ]["content"]
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as error:
        raise ValueError(
            "Ollama response does not contain valid text output"
        ) from error

    if not isinstance(response_text, str):
        raise ValueError(
            "Ollama response text is invalid"
        )

    input_tokens = ollama_response.get(
        "prompt_eval_count",
        0,
    )
    output_tokens = ollama_response.get(
        "eval_count",
        0,
    )

    return {
        "provider": "ollama",
        "model_id": ollama_response.get(
            "model",
            model_id.strip(),
        ),
        "response_text": response_text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (
                input_tokens + output_tokens
            ),
        },
        "stop_reason": ollama_response.get(
            "done_reason"
        ),
    }