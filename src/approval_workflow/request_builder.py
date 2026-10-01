"""Build human approval requests from validated investigations."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from uuid import UUID
from uuid import uuid4


APPROVAL_TTL = timedelta(hours=24)

ALLOWED_PROVIDERS = {
    "bedrock",
    "ollama",
}

ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


def require_uuid(value: Any, field_name: str) -> str:
    """Return one validated UUID string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a valid UUID"
        )

    try:
        UUID(value)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a valid UUID"
        ) from error

    return value


def format_utc_timestamp(value: datetime) -> str:
    """Return one timezone-aware datetime in UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "now must include timezone information"
        )

    return (
        value
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def create_approval_request(
    finding_id: str,
    result: dict[str, Any],
    investigation_key: str,
    approval_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create one pending, dry-run approval request."""
    validated_finding_id = require_uuid(
        finding_id,
        "finding_id",
    )

    if not isinstance(result, dict):
        raise ValueError(
            "result must be an object"
        )

    provider = result.get("provider")

    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(
            "result.provider must be bedrock or ollama"
        )

    model_id = result.get("model_id")

    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError(
            "result.model_id must be a non-empty string"
        )

    investigation = result.get("investigation")

    if not isinstance(investigation, dict):
        raise ValueError(
            "result.investigation must be an object"
        )

    if investigation.get("requires_human_approval") is not True:
        raise ValueError(
            "Investigation must require human approval"
        )

    summary = investigation.get("summary")

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError(
            "investigation.summary must be a non-empty string"
        )

    confidence = investigation.get("confidence")

    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(
            "investigation.confidence is invalid"
        )

    proposed_actions = investigation.get(
        "recommended_actions"
    )

    if (
        not isinstance(proposed_actions, list)
        or not proposed_actions
        or not all(
            isinstance(action, str) and action.strip()
            for action in proposed_actions
        )
    ):
        raise ValueError(
            "investigation.recommended_actions is invalid"
        )

    expected_key = (
        f"ai-investigations/{validated_finding_id}.json"
    )

    if investigation_key != expected_key:
        raise ValueError(
            "investigation_key does not match finding_id"
        )

    selected_approval_id = require_uuid(
        approval_id or str(uuid4()),
        "approval_id",
    )

    current_time = now or datetime.now(timezone.utc)
    expires_at = current_time + APPROVAL_TTL

    return {
        "schema_version": "1.0.0",
        "approval_id": selected_approval_id,
        "finding_id": validated_finding_id,
        "investigation_key": investigation_key,
        "provider": provider,
        "model_id": model_id,
        "summary": summary,
        "confidence": confidence,
        "proposed_actions": list(proposed_actions),
        "status": "PENDING",
        "requested_at": format_utc_timestamp(
            current_time
        ),
        "expires_at": format_utc_timestamp(
            expires_at
        ),
        "requires_human_approval": True,
        "response_mode": "DRY_RUN",
    }