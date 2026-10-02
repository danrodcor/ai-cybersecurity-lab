"""Create and persist approved dry-run response records."""

import json
import logging
import os
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def require_string(
    value: Any,
    field_name: str,
) -> str:
    """Return one required non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    return value.strip()


def require_uuid(
    value: Any,
    field_name: str,
) -> str:
    """Return one canonical UUID string."""
    candidate = require_string(value, field_name)

    try:
        return str(uuid.UUID(candidate))
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a UUID"
        ) from error


def required_environment_variable(name: str) -> str:
    """Return one required environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def format_utc_timestamp(value: datetime) -> str:
    """Format one timezone-aware timestamp in UTC."""
    if value.tzinfo is None:
        raise ValueError(
            "Timestamp must include timezone information"
        )

    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def create_dry_run_response(
    event: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a simulated response from an approved decision."""
    if not isinstance(event, dict):
        raise ValueError("event must be an object")

    finding_id = require_uuid(
        event.get("finding_id"),
        "event.finding_id",
    )
    approval_id = require_uuid(
        event.get("approval_id"),
        "event.approval_id",
    )
    decision = require_string(
        event.get("decision"),
        "event.decision",
    )
    response_mode = require_string(
        event.get("response_mode"),
        "event.response_mode",
    )
    decided_by = require_string(
        event.get("decided_by"),
        "event.decided_by",
    )
    approval_decision_key = require_string(
        event.get("approval_decision_key"),
        "event.approval_decision_key",
    )

    if decision != "APPROVED":
        raise ValueError(
            "Dry-run response requires an approved decision"
        )

    if response_mode != "DRY_RUN":
        raise ValueError(
            "Dry-run response requires DRY_RUN mode"
        )

    proposed_actions = event.get("proposed_actions")

    if (
        not isinstance(proposed_actions, list)
        or not proposed_actions
        or len(proposed_actions) > 15
        or not all(
            isinstance(action, str)
            and action.strip()
            and len(action) <= 500
            for action in proposed_actions
        )
    ):
        raise ValueError(
            "event.proposed_actions is invalid"
        )

    current_time = now or datetime.now(timezone.utc)

    response_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            (
                f"dry-run-response:"
                f"{finding_id}:{approval_id}"
            ),
        )
    )

    return {
        "schema_version": "1.0.0",
        "response_id": response_id,
        "finding_id": finding_id,
        "approval_id": approval_id,
        "approval_decision_key": approval_decision_key,
        "decision": decision,
        "decided_by": decided_by,
        "response_mode": response_mode,
        "status": "SIMULATED",
        "executed": False,
        "simulated_at": format_utc_timestamp(
            current_time
        ),
        "simulated_actions": [
            {
                "action": action.strip(),
                "status": "NOT_EXECUTED",
            }
            for action in proposed_actions
        ],
        "resource_changes": 0,
        "summary": (
            "Approved response actions were simulated. "
            "No cloud resource was modified."
        ),
    }


def persist_dry_run_response(
    response: dict[str, Any],
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
) -> dict[str, Any]:
    """Persist one validated simulated response."""
    if not isinstance(response, dict):
        raise ValueError(
            "response must be an object"
        )

    finding_id = require_uuid(
        response.get("finding_id"),
        "response.finding_id",
    )
    approval_id = require_uuid(
        response.get("approval_id"),
        "response.approval_id",
    )

    if response.get("decision") != "APPROVED":
        raise ValueError(
            "Response decision must be APPROVED"
        )

    if response.get("response_mode") != "DRY_RUN":
        raise ValueError(
            "Response mode must be DRY_RUN"
        )

    if response.get("status") != "SIMULATED":
        raise ValueError(
            "Response status must be SIMULATED"
        )

    if response.get("executed") is not False:
        raise ValueError(
            "Dry-run response cannot execute actions"
        )

    if response.get("resource_changes") != 0:
        raise ValueError(
            "Dry-run response cannot change resources"
        )

    bucket_name = required_environment_variable(
        "EVIDENCE_BUCKET_NAME"
    )
    table_name = required_environment_variable(
        "INCIDENT_TABLE_NAME"
    )

    if s3_client is None or dynamodb_client is None:
        import boto3

        if s3_client is None:
            s3_client = boto3.client("s3")

        if dynamodb_client is None:
            dynamodb_client = boto3.client(
                "dynamodb"
            )

    response_key = (
        f"dry-run-responses/{finding_id}/"
        f"{approval_id}.json"
    )

    body = json.dumps(
        response,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=response_key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    dynamodb_client.update_item(
        TableName=table_name,
        Key={
            "finding_id": {
                "S": finding_id,
            },
        },
        UpdateExpression=(
            "SET response_status = :response_status, "
            "response_mode = :response_mode, "
            "response_key = :response_key, "
            "response_simulated_at = :simulated_at, "
            "response_executed = :executed"
        ),
        ConditionExpression=(
            "attribute_exists(finding_id) AND "
            "approval_id = :approval_id AND "
            "approval_status = :approved AND "
            "approval_response_mode = :response_mode"
        ),
        ExpressionAttributeValues={
            ":response_status": {
                "S": "SIMULATED",
            },
            ":response_mode": {
                "S": "DRY_RUN",
            },
            ":response_key": {
                "S": response_key,
            },
            ":simulated_at": {
                "S": response["simulated_at"],
            },
            ":executed": {
                "BOOL": False,
            },
            ":approval_id": {
                "S": approval_id,
            },
            ":approved": {
                "S": "APPROVED",
            },
        },
    )

    return {
        "bucket_name": bucket_name,
        "table_name": table_name,
        "response_key": response_key,
        "response_status": "SIMULATED",
        "response_mode": "DRY_RUN",
    }


def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Create and persist one simulated response."""
    response = create_dry_run_response(event)
    persistence = persist_dry_run_response(response)

    LOGGER.info(
        json.dumps(
            {
                "event": "dry_run_response_simulated",
                "finding_id": response["finding_id"],
                "approval_id": response["approval_id"],
                "response_id": response["response_id"],
                "resource_changes": 0,
                "executed": False,
            },
            separators=(",", ":"),
        )
    )

    return {
        "dry_run_response": response,
        "persistence": persistence,
    }