"""Persist AI investigation results without executing response actions."""

import json
import os
from datetime import datetime
from datetime import timezone
from typing import Any


def required_environment_variable(name: str) -> str:
    """Return one required environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def persist_investigation(
    finding_id: str,
    result: dict[str, Any],
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Persist one validated AI investigation."""
    if not isinstance(finding_id, str) or not finding_id.strip():
        raise ValueError(
            "finding_id must be a non-empty string"
        )

    model_id = result.get("model_id")
    investigation = result.get("investigation")

    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError(
            "result.model_id must be a non-empty string"
        )

    if not isinstance(investigation, dict):
        raise ValueError(
            "result.investigation must be an object"
        )

    if investigation.get("requires_human_approval") is not True:
        raise ValueError(
            "Investigation must require human approval"
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

    current_time = now or datetime.now(timezone.utc)
    investigated_at = (
        current_time
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    investigation_key = (
        f"ai-investigations/{finding_id}.json"
    )

    document = {
        "finding_id": finding_id,
        "investigated_at": investigated_at,
        "model_id": model_id,
        "investigation": investigation,
        "usage": result.get("usage", {}),
        "stop_reason": result.get("stop_reason"),
    }

    body = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=investigation_key,
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
            "SET investigation_key = :key, "
            "investigation_status = :status, "
            "investigated_at = :investigated_at, "
            "investigation_model_id = :model_id"
        ),
        ConditionExpression=(
            "attribute_exists(finding_id)"
        ),
        ExpressionAttributeValues={
            ":key": {
                "S": investigation_key,
            },
            ":status": {
                "S": "COMPLETED",
            },
            ":investigated_at": {
                "S": investigated_at,
            },
            ":model_id": {
                "S": model_id,
            },
        },
    )

    return {
        "bucket_name": bucket_name,
        "investigation_key": investigation_key,
        "table_name": table_name,
        "investigated_at": investigated_at,
    }
