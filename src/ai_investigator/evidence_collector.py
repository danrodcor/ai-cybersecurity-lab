"""Build a size-limited, allow-listed evidence package."""

import json
from typing import Any


DEFAULT_MAX_EVIDENCE_BYTES = 16_384


def collect_evidence(
    normalized_finding: dict[str, Any],
    max_bytes: int = DEFAULT_MAX_EVIDENCE_BYTES,
) -> dict[str, Any]:
    """Return only evidence explicitly approved for AI analysis."""
    finding_id = normalized_finding.get("finding_id")

    if not isinstance(finding_id, str) or not finding_id.strip():
        raise ValueError(
            "normalized_finding.finding_id must be a non-empty string"
        )

    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError(
            "max_bytes must be a positive integer"
        )

    source = normalized_finding.get("source", {})
    severity = normalized_finding.get("severity", {})
    resource = normalized_finding.get("resource", {})
    actor = normalized_finding.get("actor", {})
    activity = normalized_finding.get("activity", {})
    timestamps = normalized_finding.get("timestamps", {})

    evidence = {
        "schema_version": normalized_finding.get(
            "schema_version"
        ),
        "finding_id": finding_id,
        "source": {
            "provider": source.get("provider"),
            "service": source.get("service"),
        },
        "finding_type": normalized_finding.get(
            "finding_type"
        ),
        "title": normalized_finding.get("title"),
        "description": normalized_finding.get(
            "description"
        ),
        "severity": {
            "score": severity.get("score"),
            "label": severity.get("label"),
        },
        "region": normalized_finding.get("region"),
        "resource": {
            "type": resource.get("type"),
            "region": resource.get("region"),
        },
        "actor": {
            "principal_type": actor.get(
                "principal_type"
            ),
            "source_ip": actor.get("source_ip"),
            "user_agent": actor.get("user_agent"),
        },
        "activity": {
            "action": activity.get("action"),
            "service": activity.get("service"),
            "api": activity.get("api"),
            "blocked": activity.get("blocked"),
        },
        "timestamps": {
            "created_at": timestamps.get("created_at"),
            "updated_at": timestamps.get("updated_at"),
        },
        "recommendation": normalized_finding.get(
            "recommendation"
        ),
        "synthetic": normalized_finding.get("synthetic"),
        "labels": normalized_finding.get("labels", []),
    }

    threat = normalized_finding.get("threat")

    if isinstance(threat, dict):
        evidence["threat"] = {
            "tactic": threat.get("tactic"),
            "technique": threat.get("technique"),
            "technique_id": threat.get("technique_id"),
        }

    evidence_size = len(
        json.dumps(
            evidence,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )

    if evidence_size > max_bytes:
        raise ValueError(
            "Allow-listed evidence exceeds the size limit"
        )

    return evidence