"""Invoke Bedrock for a structured security investigation."""

import json
import os
from typing import Any

from src.ai_investigator.prompt_builder import SYSTEM_PROMPT
from src.ai_investigator.prompt_builder import build_investigation_prompt


ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


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

    try:
        investigation = json.loads(response_text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "Bedrock response is not valid JSON"
        ) from error

    if investigation.get("confidence") not in ALLOWED_CONFIDENCE:
        raise ValueError(
            "Bedrock response has invalid confidence"
        )

    if investigation.get("requires_human_approval") is not True:
        raise ValueError(
            "Bedrock response must require human approval"
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
                f"Bedrock response field is invalid: {field_name}"
            )

    if not isinstance(investigation.get("summary"), str):
        raise ValueError(
            "Bedrock response has invalid summary"
        )

    return investigation


def investigate_finding(
    normalized_finding: dict[str, Any],
    bedrock_client: Any | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Investigate one finding without executing response actions."""
    selected_model = resolve_model_id(model_id)
    prompt = build_investigation_prompt(normalized_finding)

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
        "model_id": selected_model,
        "investigation": parse_investigation_response(
            response
        ),
        "usage": response.get("usage", {}),
        "stop_reason": response.get("stopReason"),
    }