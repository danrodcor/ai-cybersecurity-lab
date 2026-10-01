import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from jsonschema import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = PROJECT_ROOT / "schemas"

FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def load_schema(filename: str) -> dict:
    path = SCHEMA_DIRECTORY / filename

    with path.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def approval_request() -> dict:
    return {
        "schema_version": "1.0.0",
        "approval_id": APPROVAL_ID,
        "finding_id": FINDING_ID,
        "investigation_key": INVESTIGATION_KEY,
        "provider": "ollama",
        "model_id": "qwen3:14b",
        "summary": (
            "A GuardDuty finding requires human review."
        ),
        "confidence": "MEDIUM",
        "proposed_actions": [
            "Review related DNS activity.",
            "Preserve evidence for investigation.",
        ],
        "status": "PENDING",
        "requested_at": "2026-10-01T22:00:00Z",
        "expires_at": "2026-10-02T22:00:00Z",
        "requires_human_approval": True,
        "response_mode": "DRY_RUN",
    }


def approval_decision() -> dict:
    return {
        "schema_version": "1.0.0",
        "approval_id": APPROVAL_ID,
        "finding_id": FINDING_ID,
        "investigation_key": INVESTIGATION_KEY,
        "decision": "APPROVED",
        "decided_by": "security-reviewer@example.com",
        "decided_at": "2026-10-01T22:15:00Z",
        "response_mode": "DRY_RUN",
    }


class ApprovalSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request_schema = load_schema(
            "approval-request.schema.json"
        )
        cls.decision_schema = load_schema(
            "approval-decision.schema.json"
        )

        cls.request_validator = Draft202012Validator(
            cls.request_schema,
            format_checker=FormatChecker(),
        )
        cls.decision_validator = Draft202012Validator(
            cls.decision_schema,
            format_checker=FormatChecker(),
        )

    def test_schema_definitions_are_valid(self) -> None:
        Draft202012Validator.check_schema(
            self.request_schema
        )
        Draft202012Validator.check_schema(
            self.decision_schema
        )

    def test_valid_request_is_accepted(self) -> None:
        self.request_validator.validate(
            approval_request()
        )

    def test_valid_approval_is_accepted(self) -> None:
        self.decision_validator.validate(
            approval_decision()
        )

    def test_rejection_requires_comment(self) -> None:
        decision = approval_decision()
        decision["decision"] = "REJECTED"

        with self.assertRaises(ValidationError):
            self.decision_validator.validate(decision)

        decision["comment"] = (
            "Additional evidence is required."
        )
        self.decision_validator.validate(decision)

    def test_live_response_mode_is_rejected(self) -> None:
        request = approval_request()
        request["response_mode"] = "LIVE"

        with self.assertRaises(ValidationError):
            self.request_validator.validate(request)


if __name__ == "__main__":
    unittest.main(verbosity=2)