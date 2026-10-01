import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.persistence import (
    persist_approval_request,
)


FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def valid_request() -> dict:
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
            "Preserve evidence for investigation.",
        ],
        "status": "PENDING",
        "requested_at": "2026-10-01T22:30:00Z",
        "expires_at": "2026-10-02T22:30:00Z",
        "requires_human_approval": True,
        "response_mode": "DRY_RUN",
    }


class ApprovalRequestPersistenceTests(
    unittest.TestCase
):
    def test_request_is_stored_and_linked(
        self,
    ) -> None:
        request = valid_request()
        s3_client = Mock()
        dynamodb_client = Mock()

        environment = {
            "EVIDENCE_BUCKET_NAME": "test-evidence-bucket",
            "INCIDENT_TABLE_NAME": "test-incidents-table",
        }

        with patch.dict(
            "os.environ",
            environment,
            clear=True,
        ):
            result = persist_approval_request(
                request,
                s3_client=s3_client,
                dynamodb_client=dynamodb_client,
            )

        expected_key = (
            "approval-requests/"
            f"{FINDING_ID}/{APPROVAL_ID}.json"
        )

        s3_client.put_object.assert_called_once()
        s3_request = s3_client.put_object.call_args.kwargs

        self.assertEqual(
            s3_request["Bucket"],
            "test-evidence-bucket",
        )
        self.assertEqual(
            s3_request["Key"],
            expected_key,
        )
        self.assertEqual(
            s3_request["ContentType"],
            "application/json",
        )
        self.assertEqual(
            s3_request["ServerSideEncryption"],
            "AES256",
        )
        self.assertEqual(
            json.loads(s3_request["Body"]),
            request,
        )

        dynamodb_client.update_item.assert_called_once()
        dynamodb_request = (
            dynamodb_client.update_item.call_args.kwargs
        )

        self.assertEqual(
            dynamodb_request["TableName"],
            "test-incidents-table",
        )
        self.assertEqual(
            dynamodb_request["Key"]["finding_id"]["S"],
            FINDING_ID,
        )
        self.assertIn(
            "investigation_status = :completed",
            dynamodb_request["ConditionExpression"],
        )
        self.assertIn(
            "approval_id = :approval_id",
            dynamodb_request["ConditionExpression"],
        )

        values = dynamodb_request[
            "ExpressionAttributeValues"
        ]

        self.assertEqual(
            values[":pending"]["S"],
            "PENDING",
        )
        self.assertEqual(
            values[":completed"]["S"],
            "COMPLETED",
        )
        self.assertEqual(
            values[":response_mode"]["S"],
            "DRY_RUN",
        )
        self.assertEqual(
            result["approval_request_key"],
            expected_key,
        )
        self.assertEqual(
            result["status"],
            "PENDING",
        )

    def test_configuration_is_required(self) -> None:
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "EVIDENCE_BUCKET_NAME",
            ):
                persist_approval_request(
                    valid_request(),
                    s3_client=Mock(),
                    dynamodb_client=Mock(),
                )

    def test_non_pending_request_is_rejected(
        self,
    ) -> None:
        request = valid_request()
        request["status"] = "APPROVED"

        with self.assertRaisesRegex(
            ValueError,
            "must be PENDING",
        ):
            persist_approval_request(
                request,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )

    def test_live_response_is_rejected(self) -> None:
        request = valid_request()
        request["response_mode"] = "LIVE"

        with self.assertRaisesRegex(
            ValueError,
            "must be DRY_RUN",
        ):
            persist_approval_request(
                request,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )

    def test_human_approval_cannot_be_disabled(
        self,
    ) -> None:
        request = valid_request()
        request["requires_human_approval"] = False

        with self.assertRaisesRegex(
            ValueError,
            "must require human approval",
        ):
            persist_approval_request(
                request,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)