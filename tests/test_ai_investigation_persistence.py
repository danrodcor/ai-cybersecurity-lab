import json
import sys
import unittest
from datetime import datetime
from datetime import timezone
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_investigator.persistence import persist_investigation


def valid_result() -> dict:
    return {
        "provider": "ollama",
        "model_id": "test-model",
        "investigation": {
            "schema_version": "1.0.0",
            "summary": "Suspicious DNS activity was observed.",
            "confidence": "HIGH",
            "observed_facts": [
                "The finding reports a DNS request.",
            ],
            "hypotheses": [
                "The instance may have contacted a malicious domain.",
            ],
            "recommended_actions": [
                "Review DNS and process telemetry.",
            ],
            "requires_human_approval": True,
        },
        "usage": {
            "inputTokens": 250,
            "outputTokens": 80,
            "totalTokens": 330,
        },
        "stop_reason": "end_turn",
    }


class AiInvestigationPersistenceTests(unittest.TestCase):
    def test_persist_investigation_writes_and_links_result(
        self,
    ) -> None:
        finding_id = "finding-001"
        s3_client = Mock()
        dynamodb_client = Mock()
        fixed_time = datetime(
            2026,
            9,
            29,
            22,
            0,
            tzinfo=timezone.utc,
        )

        environment = {
            "EVIDENCE_BUCKET_NAME": "test-evidence-bucket",
            "INCIDENT_TABLE_NAME": "test-incidents-table",
        }

        with patch.dict(
            "os.environ",
            environment,
            clear=True,
        ):
            result = persist_investigation(
                finding_id,
                valid_result(),
                s3_client=s3_client,
                dynamodb_client=dynamodb_client,
                now=fixed_time,
            )

        s3_client.put_object.assert_called_once()
        s3_request = s3_client.put_object.call_args.kwargs

        self.assertEqual(
            s3_request["Bucket"],
            "test-evidence-bucket",
        )
        self.assertEqual(
            s3_request["Key"],
            "ai-investigations/finding-001.json",
        )
        self.assertEqual(
            s3_request["ContentType"],
            "application/json",
        )
        self.assertEqual(
            s3_request["ServerSideEncryption"],
            "AES256",
        )

        stored_document = json.loads(s3_request["Body"])

        self.assertEqual(
            stored_document["finding_id"],
            finding_id,
        )
        self.assertEqual(
            stored_document["model_id"],
            "test-model",
        )
        self.assertEqual(
            stored_document["provider"],
            "ollama",
        )
        self.assertEqual(
            stored_document["investigated_at"],
            "2026-09-29T22:00:00Z",
        )
        self.assertTrue(
            stored_document["investigation"][
                "requires_human_approval"
            ]
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
            finding_id,
        )
        self.assertEqual(
            dynamodb_request["ConditionExpression"],
            "attribute_exists(finding_id)",
        )
        self.assertEqual(
            dynamodb_request[
                "ExpressionAttributeValues"
            ][":status"]["S"],
            "COMPLETED",
        )
        self.assertEqual(
            dynamodb_request[
                "ExpressionAttributeValues"
            ][":provider"]["S"],
            "ollama",
        )
        self.assertEqual(
            result["investigation_key"],
            "ai-investigations/finding-001.json",
        )

    def test_persist_investigation_requires_configuration(
        self,
    ) -> None:
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "EVIDENCE_BUCKET_NAME",
            ):
                persist_investigation(
                    "finding-002",
                    valid_result(),
                    s3_client=Mock(),
                    dynamodb_client=Mock(),
                )
    def test_missing_provider_is_rejected(
        self,
    ) -> None:
        result = valid_result()
        del result["provider"]

        with self.assertRaisesRegex(
            ValueError,
            "result.provider",
        ):
            persist_investigation(
                "finding-003",
                result,
                s3_client=Mock(),
                dynamodb_client=Mock(),
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
            persist_investigation(
                "finding-003",
                result,
                s3_client=Mock(),
                dynamodb_client=Mock(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
    