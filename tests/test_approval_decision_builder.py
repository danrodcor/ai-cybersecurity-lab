import json
import sys
import unittest
from datetime import datetime
from datetime import timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.decision_builder import (
    create_approval_decision,
)


FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def pending_request() -> dict:
    return {
        "schema_version": "1.0.0",
        "approval_id": APPROVAL_ID,
        "finding_id": FINDING_ID,
        "investigation_key": INVESTIGATION_KEY,
        "provider": "ollama",
        "model_id": "qwen3:14b",
        "summary": (
            "A GuardDuty finding requires review."
        ),
        "confidence": "MEDIUM",
        "proposed_actions": [
            "Review related DNS activity.",
        ],
        "status": "PENDING",
        "requested_at": "2026-10-01T22:30:00Z",
        "expires_at": "2026-10-02T22:30:00Z",
        "requires_human_approval": True,
        "response_mode": "DRY_RUN",
    }


def review_time() -> datetime:
    return datetime(
        2026,
        10,
        1,
        23,
        0,
        tzinfo=timezone.utc,
    )


class ApprovalDecisionBuilderTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        schema_path = (
            PROJECT_ROOT
            / "schemas"
            / "approval-decision.schema.json"
        )

        with schema_path.open(
            encoding="utf-8"
        ) as schema_file:
            schema = json.load(schema_file)

        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    def test_valid_approval_matches_schema(
        self,
    ) -> None:
        decision = create_approval_decision(
            request=pending_request(),
            decision="APPROVED",
            decided_by="reviewer@example.com",
            now=review_time(),
        )

        self.validator.validate(decision)

        self.assertEqual(
            decision["decision"],
            "APPROVED",
        )
        self.assertEqual(
            decision["decided_at"],
            "2026-10-01T23:00:00Z",
        )
        self.assertEqual(
            decision["response_mode"],
            "DRY_RUN",
        )
        self.assertNotIn(
            "comment",
            decision,
        )

    def test_valid_rejection_matches_schema(
        self,
    ) -> None:
        decision = create_approval_decision(
            request=pending_request(),
            decision="REJECTED",
            decided_by="reviewer@example.com",
            comment="Additional evidence is required.",
            now=review_time(),
        )

        self.validator.validate(decision)

        self.assertEqual(
            decision["decision"],
            "REJECTED",
        )
        self.assertEqual(
            decision["comment"],
            "Additional evidence is required.",
        )

    def test_rejection_requires_comment(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "require a comment",
        ):
            create_approval_decision(
                request=pending_request(),
                decision="REJECTED",
                decided_by="reviewer@example.com",
                now=review_time(),
            )

    def test_expired_request_is_rejected(self) -> None:
        expired_time = datetime(
            2026,
            10,
            2,
            22,
            30,
            tzinfo=timezone.utc,
        )

        with self.assertRaisesRegex(
            ValueError,
            "has expired",
        ):
            create_approval_decision(
                request=pending_request(),
                decision="APPROVED",
                decided_by="reviewer@example.com",
                now=expired_time,
            )

    def test_non_pending_request_is_rejected(
        self,
    ) -> None:
        request = pending_request()
        request["status"] = "APPROVED"

        with self.assertRaisesRegex(
            ValueError,
            "Only PENDING",
        ):
            create_approval_decision(
                request=request,
                decision="APPROVED",
                decided_by="reviewer@example.com",
                now=review_time(),
            )

    def test_live_response_mode_is_rejected(
        self,
    ) -> None:
        request = pending_request()
        request["response_mode"] = "LIVE"

        with self.assertRaisesRegex(
            ValueError,
            "must be DRY_RUN",
        ):
            create_approval_decision(
                request=request,
                decision="APPROVED",
                decided_by="reviewer@example.com",
                now=review_time(),
            )

    def test_invalid_decision_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "APPROVED or REJECTED",
        ):
            create_approval_decision(
                request=pending_request(),
                decision="EXECUTE",
                decided_by="reviewer@example.com",
                now=review_time(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)