import json
import sys
import unittest
from datetime import datetime
from datetime import timezone
from pathlib import Path
from uuid import UUID

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.request_builder import (
    create_approval_request,
)


FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def valid_result() -> dict:
    return {
        "provider": "ollama",
        "model_id": "qwen3:14b",
        "investigation": {
            "schema_version": "1.0.0",
            "summary": (
                "A GuardDuty finding requires review."
            ),
            "confidence": "MEDIUM",
            "observed_facts": [
                "A suspicious DNS request was observed.",
            ],
            "hypotheses": [
                "The instance may require investigation.",
            ],
            "recommended_actions": [
                "Review related DNS activity.",
                "Preserve evidence for investigation.",
            ],
            "requires_human_approval": True,
        },
        "usage": {
            "total_tokens": 500,
        },
        "stop_reason": "stop",
    }


class ApprovalRequestBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_path = (
            PROJECT_ROOT
            / "schemas"
            / "approval-request.schema.json"
        )

        with schema_path.open(
            encoding="utf-8"
        ) as schema_file:
            schema = json.load(schema_file)

        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    def test_request_matches_schema(self) -> None:
        fixed_time = datetime(
            2026,
            10,
            1,
            22,
            30,
            tzinfo=timezone.utc,
        )

        request = create_approval_request(
            finding_id=FINDING_ID,
            result=valid_result(),
            investigation_key=INVESTIGATION_KEY,
            approval_id=APPROVAL_ID,
            now=fixed_time,
        )

        self.validator.validate(request)

        self.assertEqual(
            request["approval_id"],
            APPROVAL_ID,
        )
        self.assertEqual(
            request["status"],
            "PENDING",
        )
        self.assertEqual(
            request["response_mode"],
            "DRY_RUN",
        )
        self.assertEqual(
            request["requested_at"],
            "2026-10-01T22:30:00Z",
        )
        self.assertEqual(
            request["expires_at"],
            "2026-10-02T22:30:00Z",
        )
        self.assertEqual(
            request["proposed_actions"],
            valid_result()["investigation"][
                "recommended_actions"
            ],
        )

    def test_approval_id_is_generated(self) -> None:
        request = create_approval_request(
            finding_id=FINDING_ID,
            result=valid_result(),
            investigation_key=INVESTIGATION_KEY,
        )

        UUID(request["approval_id"])

    def test_mismatched_investigation_key_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "does not match finding_id",
        ):
            create_approval_request(
                finding_id=FINDING_ID,
                result=valid_result(),
                investigation_key=(
                    "ai-investigations/"
                    "00000000-0000-0000-0000-000000000000"
                    ".json"
                ),
            )

    def test_unsafe_investigation_is_rejected(
        self,
    ) -> None:
        result = valid_result()
        result["investigation"][
            "requires_human_approval"
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            "must require human approval",
        ):
            create_approval_request(
                finding_id=FINDING_ID,
                result=result,
                investigation_key=INVESTIGATION_KEY,
            )

    def test_invalid_provider_is_rejected(self) -> None:
        result = valid_result()
        result["provider"] = "remote-http"

        with self.assertRaisesRegex(
            ValueError,
            "provider",
        ):
            create_approval_request(
                finding_id=FINDING_ID,
                result=result,
                investigation_key=INVESTIGATION_KEY,
            )

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "timezone",
        ):
            create_approval_request(
                finding_id=FINDING_ID,
                result=valid_result(),
                investigation_key=INVESTIGATION_KEY,
                now=datetime(2026, 10, 1, 22, 30),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)