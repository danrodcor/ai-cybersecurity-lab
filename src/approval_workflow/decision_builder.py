"""Build immutable human approval decisions."""

from datetime import datetime
from datetime import timezone
from typing import Any

from .request_builder import format_utc_timestamp
from .request_builder import require_uuid


ALLOWED_DECISIONS = {
    "APPROVED",
    "REJECTED",
}


def parse_timestamp(
    value: Any,
    field_name: str,
) -> datetime:
    """Parse one timezone-aware ISO 8601 timestamp."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a valid timestamp"
        )

    timestamp = value

    if timestamp.endswith("Z"):
        timestamp = (
            timestamp[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a valid timestamp"
        ) from error

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"{field_name} must include timezone information"
        )

    return parsed.astimezone(timezone.utc)


def create_approval_decision(
    request: dict[str, Any],
    decision: str,
    decided_by: str,
    comment: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create one immutable human approval decision."""
    if not isinstance(request, dict):
        raise ValueError(
            "request must be an object"
        )

    if request.get("status") != "PENDING":
        raise ValueError(
            "Only PENDING requests can be decided"
        )

    if request.get("requires_human_approval") is not True:
        raise ValueError(
            "Request must require human approval"
        )

    if request.get("response_mode") != "DRY_RUN":
        raise ValueError(
            "request.response_mode must be DRY_RUN"
        )

    approval_id = require_uuid(
        request.get("approval_id"),
        "request.approval_id",
    )
    finding_id = require_uuid(
        request.get("finding_id"),
        "request.finding_id",
    )

    investigation_key = request.get(
        "investigation_key"
    )

    if (
        not isinstance(investigation_key, str)
        or not investigation_key.strip()
    ):
        raise ValueError(
            "request.investigation_key must be "
            "a non-empty string"
        )

    if decision not in ALLOWED_DECISIONS:
        raise ValueError(
            "decision must be APPROVED or REJECTED"
        )

    if (
        not isinstance(decided_by, str)
        or not decided_by.strip()
    ):
        raise ValueError(
            "decided_by must be a non-empty string"
        )

    if decision == "REJECTED":
        if (
            not isinstance(comment, str)
            or not comment.strip()
        ):
            raise ValueError(
                "Rejected decisions require a comment"
            )

    if comment is not None:
        if not isinstance(comment, str) or not comment.strip():
            raise ValueError(
                "comment must be a non-empty string"
            )

    current_time = now or datetime.now(timezone.utc)

    if (
        current_time.tzinfo is None
        or current_time.utcoffset() is None
    ):
        raise ValueError(
            "now must include timezone information"
        )

    expires_at = parse_timestamp(
        request.get("expires_at"),
        "request.expires_at",
    )

    if current_time.astimezone(timezone.utc) >= expires_at:
        raise ValueError(
            "Approval request has expired"
        )

    result = {
        "schema_version": "1.0.0",
        "approval_id": approval_id,
        "finding_id": finding_id,
        "investigation_key": investigation_key,
        "decision": decision,
        "decided_by": decided_by,
        "decided_at": format_utc_timestamp(
            current_time
        ),
        "response_mode": "DRY_RUN",
    }

    if comment is not None:
        result["comment"] = comment

    return result