import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.persistence import (
    persist_approval_decision,
)


FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def valid_decision() -> dict:
    return {
        "schema_version": "1.0.0",
        "approval_id": APPROVAL_ID,
        "finding_id": FINDING_ID,
        "investigation_key": INVESTIGATION_KEY,
        "decision": "APPROVED",
        "decided_by": "reviewer@example.com",
        "decided_at": "2026-10-01T23:00:00Z",
        "response_mode": "DRY_RUN",
    }


class ApprovalDecisionPersistenceTests(
    unittest.TestCase
):
    def test_approval_is_stored_and_linked(
        self,
    ) -> None:
        decision = valid_decision()
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
            result = persist_approval_decision(
                decision,
                s3_client=s3_client,
                dynamodb_client=dynamodb_client,
            )

        expected_key = (
            "approval-decisions/"
            f"{FINDING_ID}/{APPROVAL_ID}/approved.json"
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
            decision,
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
            "approval_status = :pending",
            dynamodb_request["ConditionExpression"],
        )
        self.assertIn(
            "approval_status = :decision",
            dynamodb_request["ConditionExpression"],
        )
        self.assertIn(
            "approval_investigation_key",
            dynamodb_request["ConditionExpression"],
        )

        values = dynamodb_request[
            "ExpressionAttributeValues"
        ]

        self.assertEqual(
            values[":decision"]["S"],
            "APPROVED",
        )
        self.assertEqual(
            values[":pending"]["S"],
            "PENDING",
        )
        self.assertNotIn(
            ":comment",
            values,
        )
        self.assertEqual(
            result["approval_decision_key"],
            expected_key,
        )
        self.assertEqual(
            result["decision"],
            "APPROVED",
        )

    def test_rejection_comment_is_persisted(
        self,
    ) -> None:
        decision = valid_decision()
        decision["decision"] = "REJECTED"
        decision["comment"] = (
            "Additional evidence is required."
        )

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
            result = persist_approval_decision(
                decision,
                s3_client=s3_client,
                dynamodb_client=dynamodb_client,
            )

        dynamodb_request = (
            dynamodb_client.update_item.call_args.kwargs
        )
        values = dynamodb_request[
            "ExpressionAttributeValues"
        ]

        self.assertIn(
            "approval_comment = :comment",
            dynamodb_request["UpdateExpression"],
        )
        self.assertEqual(
            values[":comment"]["S"],
            "Additional evidence is required.",
        )
        self.assertTrue(
            result["approval_decision_key"].endswith(
                "/rejected.json"
            )
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
                persist_approval_decision(
                    valid_decision(),
                    s3_client=Mock(),
                    dynamodb_client=Mock(),
                )

    def test_live_response_is_rejected(self) -> None:
        decision = valid_decision()
        decision["response_mode"] = "LIVE"

        with self.assertRaisesRegex(
            ValueError,
            "must be DRY_RUN",
        ):
            persist_approval_decision(
                decision,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )

    def test_invalid_decision_is_rejected(self) -> None:
        decision = valid_decision()
        decision["decision"] = "EXECUTE"

        with self.assertRaisesRegex(
            ValueError,
            "APPROVED or REJECTED",
        ):
            persist_approval_decision(
                decision,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)