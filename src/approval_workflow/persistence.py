"""Persist pending human approval requests."""

import json
import os
from typing import Any


def required_environment_variable(name: str) -> str:
    """Return one required environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def persist_approval_request(
    request: dict[str, Any],
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
) -> dict[str, Any]:
    """Persist one safe, pending approval request."""
    if not isinstance(request, dict):
        raise ValueError(
            "request must be an object"
        )

    finding_id = request.get("finding_id")
    approval_id = request.get("approval_id")
    investigation_key = request.get(
        "investigation_key"
    )

    for field_name, field_value in (
        ("finding_id", finding_id),
        ("approval_id", approval_id),
        ("investigation_key", investigation_key),
    ):
        if (
            not isinstance(field_value, str)
            or not field_value.strip()
        ):
            raise ValueError(
                f"request.{field_name} must be a "
                "non-empty string"
            )

    if request.get("status") != "PENDING":
        raise ValueError(
            "request.status must be PENDING"
        )

    if request.get("requires_human_approval") is not True:
        raise ValueError(
            "Request must require human approval"
        )

    if request.get("response_mode") != "DRY_RUN":
        raise ValueError(
            "request.response_mode must be DRY_RUN"
        )

    requested_at = request.get("requested_at")
    expires_at = request.get("expires_at")

    if (
        not isinstance(requested_at, str)
        or not requested_at.strip()
        or not isinstance(expires_at, str)
        or not expires_at.strip()
    ):
        raise ValueError(
            "Request timestamps must be non-empty strings"
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
            dynamodb_client = boto3.client("dynamodb")

    approval_request_key = (
        f"approval-requests/{finding_id}/{approval_id}.json"
    )

    body = json.dumps(
        request,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=approval_request_key,
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
            "SET approval_id = :approval_id, "
            "approval_status = :pending, "
            "approval_request_key = :request_key, "
            "approval_requested_at = :requested_at, "
            "approval_expires_at = :expires_at, "
            "approval_response_mode = :response_mode, "
            "approval_investigation_key = "
            ":investigation_key"
        ),
        ConditionExpression=(
            "attribute_exists(finding_id) "
            "AND investigation_status = :completed "
            "AND (attribute_not_exists(approval_id) "
            "OR approval_id = :approval_id)"
        ),
        ExpressionAttributeValues={
            ":approval_id": {
                "S": approval_id,
            },
            ":pending": {
                "S": "PENDING",
            },
            ":request_key": {
                "S": approval_request_key,
            },
            ":requested_at": {
                "S": requested_at,
            },
            ":expires_at": {
                "S": expires_at,
            },
            ":response_mode": {
                "S": "DRY_RUN",
            },
            ":investigation_key": {
                "S": investigation_key,
            },
            ":completed": {
                "S": "COMPLETED",
            },
        },
    )

    return {
        "bucket_name": bucket_name,
        "approval_request_key": approval_request_key,
        "table_name": table_name,
        "approval_id": approval_id,
        "status": "PENDING",
    }

def persist_approval_decision(
    decision: dict[str, Any],
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
) -> dict[str, Any]:
    """Persist one immutable human approval decision."""
    if not isinstance(decision, dict):
        raise ValueError(
            "decision must be an object"
        )

    finding_id = decision.get("finding_id")
    approval_id = decision.get("approval_id")
    investigation_key = decision.get(
        "investigation_key"
    )
    decision_value = decision.get("decision")
    decided_by = decision.get("decided_by")
    decided_at = decision.get("decided_at")

    for field_name, field_value in (
        ("finding_id", finding_id),
        ("approval_id", approval_id),
        ("investigation_key", investigation_key),
        ("decided_by", decided_by),
        ("decided_at", decided_at),
    ):
        if (
            not isinstance(field_value, str)
            or not field_value.strip()
        ):
            raise ValueError(
                f"decision.{field_name} must be a "
                "non-empty string"
            )

    if decision_value not in {
        "APPROVED",
        "REJECTED",
    }:
        raise ValueError(
            "decision.decision must be APPROVED or REJECTED"
        )

    if decision.get("response_mode") != "DRY_RUN":
        raise ValueError(
            "decision.response_mode must be DRY_RUN"
        )

    comment = decision.get("comment")

    if decision_value == "REJECTED":
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
                "decision.comment must be a non-empty string"
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
            dynamodb_client = boto3.client("dynamodb")

    decision_name = decision_value.lower()
    approval_decision_key = (
        f"approval-decisions/{finding_id}/"
        f"{approval_id}/{decision_name}.json"
    )

    body = json.dumps(
        decision,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=approval_decision_key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    update_fields = [
        "approval_status = :decision",
        "approval_decision_key = :decision_key",
        "approval_decided_by = :decided_by",
        "approval_decided_at = :decided_at",
    ]

    values = {
        ":approval_id": {
            "S": approval_id,
        },
        ":pending": {
            "S": "PENDING",
        },
        ":decision": {
            "S": decision_value,
        },
        ":decision_key": {
            "S": approval_decision_key,
        },
        ":decided_by": {
            "S": decided_by,
        },
        ":decided_at": {
            "S": decided_at,
        },
        ":investigation_key": {
            "S": investigation_key,
        },
    }

    if comment is not None:
        update_fields.append(
            "approval_comment = :comment"
        )
        values[":comment"] = {
            "S": comment,
        }

    dynamodb_client.update_item(
        TableName=table_name,
        Key={
            "finding_id": {
                "S": finding_id,
            },
        },
        UpdateExpression=(
            "SET "
            + ", ".join(update_fields)
        ),
        ConditionExpression=(
            "attribute_exists(finding_id) "
            "AND approval_id = :approval_id "
            "AND approval_investigation_key = "
            ":investigation_key "
            "AND (approval_status = :pending "
            "OR (approval_status = :decision "
            "AND approval_decision_key = "
            ":decision_key))"
        ),
        ExpressionAttributeValues=values,
    )

    return {
        "bucket_name": bucket_name,
        "approval_decision_key": approval_decision_key,
        "table_name": table_name,
        "approval_id": approval_id,
        "decision": decision_value,
    }