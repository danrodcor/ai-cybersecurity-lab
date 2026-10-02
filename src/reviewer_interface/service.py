"""Read pending approvals and invoke the decision Lambda."""

import json
from typing import Any


ALLOWED_DECISIONS = {
    "APPROVED",
    "REJECTED",
}

REQUIRED_REQUEST_FIELDS = {
    "approval_id",
    "finding_id",
    "investigation_key",
    "provider",
    "model_id",
    "summary",
    "confidence",
    "proposed_actions",
    "status",
    "requested_at",
    "expires_at",
    "requires_human_approval",
    "response_mode",
}


def _string_attribute(
    item: dict[str, Any],
    name: str,
) -> str:
    """Return one required DynamoDB string attribute."""
    try:
        value = item[name]["S"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            f"Missing DynamoDB string attribute: {name}"
        ) from error

    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Invalid DynamoDB string attribute: {name}"
        )

    return value


def list_pending_approvals(
    dynamodb_client: Any,
    table_name: str,
) -> list[dict[str, str]]:
    """Return pending approval metadata ordered by request time."""
    approvals: list[dict[str, str]] = []
    exclusive_start_key = None

    while True:
        request: dict[str, Any] = {
            "TableName": table_name,
            "FilterExpression": "#status = :pending",
            "ExpressionAttributeNames": {
                "#status": "approval_status",
            },
            "ExpressionAttributeValues": {
                ":pending": {
                    "S": "PENDING",
                },
            },
            "ProjectionExpression": (
                "finding_id, approval_id, "
                "approval_request_key, "
                "approval_requested_at, "
                "approval_expires_at, "
                "approval_response_mode"
            ),
        }

        if exclusive_start_key is not None:
            request["ExclusiveStartKey"] = (
                exclusive_start_key
            )

        response = dynamodb_client.scan(**request)

        for item in response.get("Items", []):
            approvals.append(
                {
                    "finding_id": _string_attribute(
                        item,
                        "finding_id",
                    ),
                    "approval_id": _string_attribute(
                        item,
                        "approval_id",
                    ),
                    "request_key": _string_attribute(
                        item,
                        "approval_request_key",
                    ),
                    "requested_at": _string_attribute(
                        item,
                        "approval_requested_at",
                    ),
                    "expires_at": _string_attribute(
                        item,
                        "approval_expires_at",
                    ),
                    "response_mode": _string_attribute(
                        item,
                        "approval_response_mode",
                    ),
                }
            )

        exclusive_start_key = response.get(
            "LastEvaluatedKey"
        )

        if exclusive_start_key is None:
            break

    return sorted(
        approvals,
        key=lambda approval: approval["requested_at"],
    )


def validate_approval_request(
    request: dict[str, Any],
) -> dict[str, Any]:
    """Validate the safety-critical approval fields."""
    if not isinstance(request, dict):
        raise ValueError(
            "Approval request must be an object"
        )

    missing_fields = (
        REQUIRED_REQUEST_FIELDS - request.keys()
    )

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            f"Approval request is missing fields: {missing}"
        )

    if request["status"] != "PENDING":
        raise ValueError(
            "Approval request must be pending"
        )

    if request["response_mode"] != "DRY_RUN":
        raise ValueError(
            "Approval request must use DRY_RUN"
        )

    if request["requires_human_approval"] is not True:
        raise ValueError(
            "Approval request must require human approval"
        )

    return request


def load_approval_request(
    s3_client: Any,
    bucket_name: str,
    request_key: str,
) -> dict[str, Any]:
    """Load and validate one approval request from S3."""
    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=request_key,
    )

    try:
        document = json.loads(
            response["Body"].read()
        )
    except (
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        raise ValueError(
            "Approval request evidence is invalid"
        ) from error

    if isinstance(document, dict):
        document = document.get(
            "approval_request",
            document,
        )

    return validate_approval_request(document)


def submit_decision(
    lambda_client: Any,
    function_name: str,
    approval_request: dict[str, Any],
    decision: str,
    decided_by: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Invoke the approval-decision Lambda synchronously."""
    request = validate_approval_request(
        approval_request
    )
    selected_decision = decision.strip().upper()
    reviewer = decided_by.strip()

    if selected_decision not in ALLOWED_DECISIONS:
        raise ValueError(
            "Decision must be APPROVED or REJECTED"
        )

    if not reviewer:
        raise ValueError(
            "Reviewer identity is required"
        )

    normalized_comment = (
        comment.strip()
        if isinstance(comment, str)
        else None
    )

    if (
        selected_decision == "REJECTED"
        and not normalized_comment
    ):
        raise ValueError(
            "Rejected decisions require a comment"
        )

    payload = {
        "approval_request": request,
        "decision": selected_decision,
        "decided_by": reviewer,
        "comment": normalized_comment,
    }

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8"),
    )

    try:
        result = json.loads(
            response["Payload"].read()
        )
    except (
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        raise RuntimeError(
            "Decision Lambda returned invalid JSON"
        ) from error

    if response.get("FunctionError"):
        message = result.get(
            "errorMessage",
            "Decision Lambda failed",
        )
        raise RuntimeError(message)

    decision_result = result.get(
        "approval_decision"
    )

    if not isinstance(decision_result, dict):
        raise RuntimeError(
            "Decision Lambda returned no decision"
        )

    if decision_result.get("response_mode") != "DRY_RUN":
        raise RuntimeError(
            "Decision Lambda returned an unsafe mode"
        )

    if decision_result.get("decision") != selected_decision:
        raise RuntimeError(
            "Decision Lambda returned a mismatched decision"
        )

    return result