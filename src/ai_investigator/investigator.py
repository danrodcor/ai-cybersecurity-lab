"""Investigate findings with validated AI model providers."""

import json
import os
from typing import Any

from src.ai_investigator.prompt_builder import SYSTEM_PROMPT
from src.ai_investigator.prompt_builder import build_investigation_prompt
from src.ai_investigator.evidence_collector import collect_evidence
from src.ai_investigator.ollama_client import DEFAULT_OLLAMA_ENDPOINT
from src.ai_investigator.ollama_client import invoke_ollama


ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

DEFAULT_OLLAMA_MODEL_ID = "qwen3:14b"

def resolve_model_id(model_id: str | None = None) -> str:
    """Return the explicitly configured Bedrock model identifier."""
    selected_model = (
        model_id
        or os.environ.get("BEDROCK_MODEL_ID", "")
    ).strip()

    if not selected_model:
        raise RuntimeError(
            "BEDROCK_MODEL_ID must be configured"
        )

    return selected_model

def resolve_ollama_model_id(
    model_id: str | None = None,
) -> str:
    """Return the configured local Ollama model identifier."""
    selected_model = (
        model_id
        or os.environ.get("OLLAMA_MODEL_ID")
        or DEFAULT_OLLAMA_MODEL_ID
    ).strip()

    if not selected_model:
        raise RuntimeError(
            "OLLAMA_MODEL_ID must be configured"
        )

    return selected_model

def parse_investigation_text(
    response_text: str,
    provider_name: str,
) -> dict[str, Any]:
    """Parse and validate structured investigation text."""
    if not isinstance(response_text, str):
        raise ValueError(
            f"{provider_name} response does not contain text output"
        )

    try:
        investigation = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{provider_name} response is not valid JSON"
        ) from error

    if investigation.get("schema_version") != "1.0.0":
        raise ValueError(
            (
                f"{provider_name} response has "
                "unsupported schema version"
            )
        )

    if investigation.get("confidence") not in ALLOWED_CONFIDENCE:
        raise ValueError(
            f"{provider_name} response has invalid confidence"
        )

    if investigation.get("requires_human_approval") is not True:
        raise ValueError(
            (
                f"{provider_name} response must require "
                "human approval"
            )
        )

    for field_name in (
        "observed_facts",
        "hypotheses",
        "recommended_actions",
    ):
        field_value = investigation.get(field_name)

        if (
            not isinstance(field_value, list)
            or not all(
                isinstance(item, str)
                for item in field_value
            )
        ):
            raise ValueError(
                (
                    f"{provider_name} response field "
                    f"is invalid: {field_name}"
                )
            )

    if not isinstance(investigation.get("summary"), str):
        raise ValueError(
            f"{provider_name} response has invalid summary"
        )

    return investigation


def parse_investigation_response(
    response: dict[str, Any],
) -> dict[str, Any]:
    """Parse and validate one structured Bedrock response."""
    try:
        response_text = (
            response["output"]["message"]["content"][0]["text"]
        )
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(
            "Bedrock response does not contain text output"
        ) from error

    return parse_investigation_text(
        response_text,
        provider_name="Bedrock",
    )


def investigate_finding(
    normalized_finding: dict[str, Any],
    bedrock_client: Any | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Investigate one finding without executing response actions."""
    selected_model = resolve_model_id(model_id)
    evidence = collect_evidence(normalized_finding)
    prompt = build_investigation_prompt(evidence)

    if bedrock_client is None:
        import boto3

        bedrock_client = boto3.client(
            "bedrock-runtime"
        )

    response = bedrock_client.converse(
        modelId=selected_model,
        system=[
            {
                "text": SYSTEM_PROMPT,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        inferenceConfig={
            "maxTokens": 700,
            "temperature": 0.0,
        },
    )

    return {
        "provider": "bedrock",
        "model_id": selected_model,
        "investigation": parse_investigation_response(
            response
        ),
        "usage": response.get("usage", {}),
        "stop_reason": response.get("stopReason"),
    }

def investigate_finding_locally(
    normalized_finding: dict[str, Any],
    model_id: str | None = None,
    endpoint: str = DEFAULT_OLLAMA_ENDPOINT,
    transport: Any | None = None,
) -> dict[str, Any]:
    """Investigate one finding with a local Ollama model."""
    selected_model = resolve_ollama_model_id(
        model_id
    )
    evidence = collect_evidence(normalized_finding)
    prompt = build_investigation_prompt(evidence)

    response = invoke_ollama(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        model_id=selected_model,
        endpoint=endpoint,
        transport=transport,
    )

    return {
        "provider": response["provider"],
        "model_id": response["model_id"],
        "investigation": parse_investigation_text(
            response["response_text"],
            provider_name="Ollama",
        ),
        "usage": response["usage"],
        "stop_reason": response["stop_reason"],
    }