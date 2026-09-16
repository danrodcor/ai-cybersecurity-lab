from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

SCHEMA_VERSION = "1.0.0"

THREAT_MAPPINGS = {
    "Impact:EC2/MaliciousDomainRequest.Reputation": {
        "tactic": "Command and Control",
        "technique": "Application Layer Protocol: DNS",
        "technique_id": "T1071.004",
    },
    "Trojan:EC2/DropPoint!DNS": {
        "tactic": "Command and Control",
        "technique": "Application Layer Protocol: DNS",
        "technique_id": "T1071.004",
    },
}


def severity_label(score: float) -> str:
    """Convert a GuardDuty numeric severity into an internal label."""
    if score >= 9.0:
        return "CRITICAL"

    if score >= 7.0:
        return "HIGH"

    if score >= 4.0:
        return "MEDIUM"

    return "LOW"


def require_mapping(
    container: dict[str, Any],
    key: str,
    location: str,
) -> dict[str, Any]:
    """Return a required nested dictionary or raise a clear error."""
    value = container.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"{location}.{key} must be a JSON object"
        )

    return value


def require_string(
    container: dict[str, Any],
    key: str,
    location: str,
) -> str:
    """Return a required non-empty string or raise a clear error."""
    value = container.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{location}.{key} must be a non-empty string"
        )

    return value


def first_network_interface(
    instance_details: dict[str, Any],
) -> dict[str, Any]:
    """Return the first EC2 network interface when one exists."""
    interfaces = instance_details.get("networkInterfaces", [])

    if not isinstance(interfaces, list) or not interfaces:
        return {}

    interface = interfaces[0]

    if not isinstance(interface, dict):
        return {}

    return interface


def resource_arn(
    event: dict[str, Any],
    detail: dict[str, Any],
    instance_id: str,
) -> str:
    """Resolve the EC2 ARN from the event or construct a fallback."""
    resources = event.get("resources", [])

    if isinstance(resources, list) and resources:
        first_resource = resources[0]

        if isinstance(first_resource, str) and first_resource:
            return first_resource

    account_id = require_string(
        detail,
        "accountId",
        "detail",
    )
    region = require_string(
        detail,
        "region",
        "detail",
    )

    return (
        f"arn:aws:ec2:{region}:{account_id}:"
        f"instance/{instance_id}"
    )


def recommendation_for(severity: str) -> str:
    """Return a non-destructive investigation recommendation."""
    if severity in {"CRITICAL", "HIGH"}:
        return (
            "Validate whether the DNS activity is authorized, "
            "review the instance network and process telemetry, "
            "isolate the workload if compromise is confirmed, "
            "and preserve relevant evidence."
        )

    return (
        "Review the DNS activity and instance context, "
        "confirm whether the destination is expected, "
        "and preserve relevant evidence if suspicious."
    )


def normalize_finding(
    event: dict[str, Any],
) -> dict[str, Any]:
    """Transform a GuardDuty-format EventBridge event."""
    if not isinstance(event, dict):
        raise ValueError("event must be a JSON object")

    detail = require_mapping(event, "detail", "event")
    source = require_string(event, "source", "event")
    detail_type = require_string(
        event,
        "detail-type",
        "event",
    )

    accepted_sources = {
        "aws.guardduty",
        "com.danrodcor.securitylab.guardduty",
    }

    accepted_detail_types = {
        "GuardDuty Finding",
        "Synthetic GuardDuty Finding",
    }

    if source not in accepted_sources:
        raise ValueError(f"Unsupported event source: {source}")

    if detail_type not in accepted_detail_types:
        raise ValueError(
            f"Unsupported detail-type: {detail_type}"
        )

    source_finding_id = require_string(
        detail,
        "id",
        "detail",
    )
    finding_type = require_string(
        detail,
        "type",
        "detail",
    )
    account_id = require_string(
        detail,
        "accountId",
        "detail",
    )
    region = require_string(
        detail,
        "region",
        "detail",
    )

    severity_score = detail.get("severity")

    if not isinstance(severity_score, (int, float)):
        raise ValueError(
            "detail.severity must be numeric"
        )

    if not 0.0 <= float(severity_score) <= 10.0:
        raise ValueError(
            "detail.severity must be between 0 and 10"
        )

    severity_score = float(severity_score)
    label = severity_label(severity_score)

    resource = require_mapping(
        detail,
        "resource",
        "detail",
    )
    instance_details = require_mapping(
        resource,
        "instanceDetails",
        "detail.resource",
    )
    instance_id = require_string(
        instance_details,
        "instanceId",
        "detail.resource.instanceDetails",
    )

    interface = first_network_interface(instance_details)
    public_ip = interface.get("publicIp", "0.0.0.0")

    service = require_mapping(
        detail,
        "service",
        "detail",
    )
    action = require_mapping(
        service,
        "action",
        "detail.service",
    )
    action_type = require_string(
        action,
        "actionType",
        "detail.service.action",
    )

    dns_action = action.get("dnsRequestAction", {})

    if not isinstance(dns_action, dict):
        dns_action = {}

    additional_info = service.get("additionalInfo", {})

    if not isinstance(additional_info, dict):
        additional_info = {}

    is_synthetic = bool(
        additional_info.get("synthetic", False)
    )

    normalized_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"guardduty:{region}:{account_id}:{source_finding_id}",
        )
    )

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "finding_id": normalized_id,
        "source": {
            "provider": "AWS",
            "service": "GuardDuty",
            "finding_id": source_finding_id,
        },
        "finding_type": finding_type,
        "title": require_string(
            detail,
            "title",
            "detail",
        ),
        "description": require_string(
            detail,
            "description",
            "detail",
        ),
        "severity": {
            "score": severity_score,
            "label": label,
        },
        "account_id": account_id,
        "region": region,
        "resource": {
            "type": "EC2Instance",
            "id": instance_id,
            "arn": resource_arn(
                event,
                detail,
                instance_id,
            ),
            "account_id": account_id,
            "region": region,
        },
        "actor": {
            "principal_type": "EC2Instance",
            "principal_id": instance_id,
            "source_ip": public_ip,
            "user_agent": "guardduty-event",
        },
        "activity": {
            "action": action_type,
            "service": service.get(
                "serviceName",
                "guardduty",
            ),
            "api": action_type,
            "blocked": bool(
                dns_action.get("blocked", False)
            ),
        },
        "timestamps": {
            "created_at": require_string(
                detail,
                "createdAt",
                "detail",
            ),
            "updated_at": require_string(
                detail,
                "updatedAt",
                "detail",
            ),
        },
        "recommendation": recommendation_for(label),
        "synthetic": is_synthetic,
        "labels": [
            label.lower(),
            "ec2",
            "dns-request",
            "synthetic" if is_synthetic else "provider-event",
        ],
    }

    threat = THREAT_MAPPINGS.get(finding_type)

    if threat is not None:
        normalized["threat"] = threat

    return normalized

def required_environment_variable(name: str) -> str:
    """Return one required environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def persist_finding(
    normalized: dict[str, Any],
    s3_client: Any | None = None,
    dynamodb_client: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Persist normalized evidence and searchable incident metadata."""
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

    finding_id = normalized["finding_id"]
    evidence_key = (
        f"normalized-findings/{finding_id}.json"
    )

    document = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=evidence_key,
        Body=document,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    current_time = now or datetime.now(timezone.utc)
    expires_at = int(
        (
            current_time
            + timedelta(days=30)
        ).timestamp()
    )

    dynamodb_client.put_item(
        TableName=table_name,
        Item={
            "finding_id": {
                "S": finding_id,
            },
            "source_finding_id": {
                "S": normalized["source"]["finding_id"],
            },
            "finding_type": {
                "S": normalized["finding_type"],
            },
            "severity": {
                "S": normalized["severity"]["label"],
            },
            "status": {
                "S": "NEW",
            },
            "synthetic": {
                "BOOL": normalized["synthetic"],
            },
            "account_id": {
                "S": normalized["account_id"],
            },
            "region": {
                "S": normalized["region"],
            },
            "created_at": {
                "S": normalized["timestamps"]["created_at"],
            },
            "updated_at": {
                "S": normalized["timestamps"]["updated_at"],
            },
            "evidence_key": {
                "S": evidence_key,
            },
            "expires_at": {
                "N": str(expires_at),
            },
        },
    )

    return {
        "bucket_name": bucket_name,
        "evidence_key": evidence_key,
        "table_name": table_name,
        "expires_at": expires_at,
    }

def lambda_handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """Normalize and persist one security finding."""
    normalized = normalize_finding(event)
    persistence = persist_finding(normalized)

    LOGGER.info(
        json.dumps(
            {
                "event": "finding_persisted",
                "finding_id": normalized["finding_id"],
                "source_finding_id": (
                    normalized["source"]["finding_id"]
                ),
                "severity": normalized["severity"]["label"],
                "synthetic": normalized["synthetic"],
                "evidence_key": persistence["evidence_key"],
                "expires_at": persistence["expires_at"],
            },
            separators=(",", ":"),
        )
    )

    return normalized