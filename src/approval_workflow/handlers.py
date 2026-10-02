"""Lambda handlers for the human-approval workflow."""

import json
import logging
from typing import Any

from .decision_builder import create_approval_decision
from .persistence import persist_approval_decision
from .persistence import persist_approval_request
from .request_builder import create_approval_request

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def require_mapping(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    """Return one required object."""
    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} must be an object"
        )

    return value


def require_string(
    value: Any,
    field_name: str,
) -> str:
    """Return one required non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    return value


def create_request_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Create and persist one pending approval request."""
    event = require_mapping(event, "event")

    finding_id = require_string(
        event.get("finding_id"),
        "event.finding_id",
    )
    investigation_key = require_string(
        event.get("investigation_key"),
        "event.investigation_key",
    )
    approval_id = require_string(
        event.get("approval_id"),
        "event.approval_id",
    )
    investigation_result = require_mapping(
        event.get("investigation_result"),
        "event.investigation_result",
    )

    request = create_approval_request(
        finding_id=finding_id,
        result=investigation_result,
        investigation_key=investigation_key,
        approval_id=approval_id,
    )
    persistence = persist_approval_request(request)

    LOGGER.info(
        json.dumps(
            {
                "event": "approval_request_created",
                "finding_id": finding_id,
                "approval_id": approval_id,
                "status": request["status"],
                "response_mode": request[
                    "response_mode"
                ],
            },
            separators=(",", ":"),
        )
    )

    return {
        "approval_request": request,
        "persistence": persistence,
    }


def record_decision_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Validate and persist one human decision."""
    event = require_mapping(event, "event")

    request = require_mapping(
        event.get("approval_request"),
        "event.approval_request",
    )
    decision_value = require_string(
        event.get("decision"),
        "event.decision",
    )
    decided_by = require_string(
        event.get("decided_by"),
        "event.decided_by",
    )

    decision = create_approval_decision(
        request=request,
        decision=decision_value,
        decided_by=decided_by,
        comment=event.get("comment"),
    )
    persistence = persist_approval_decision(decision)

    LOGGER.info(
        json.dumps(
            {
                "event": "approval_decision_recorded",
                "finding_id": decision["finding_id"],
                "approval_id": decision["approval_id"],
                "decision": decision["decision"],
                "response_mode": decision[
                    "response_mode"
                ],
            },
            separators=(",", ":"),
        )
    )

    return {
        "approval_decision": decision,
        "persistence": persistence,
    }