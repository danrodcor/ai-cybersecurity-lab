import json
import sys
import unittest
from datetime import datetime
from datetime import timezone
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.dry_run_response import (
    create_dry_run_response,
)
from src.approval_workflow.dry_run_response import (
    lambda_handler,
)
from src.approval_workflow.dry_run_response import (
    persist_dry_run_response,
)


SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "dry-run-response.schema.json"
)


def valid_event() -> dict:
    return {
        "finding_id": (
            "f7807877-a08a-53b4-8e2b-a2ba89e9dd96"
        ),
        "approval_id": (
            "0e51ed68-090b-4ded-8c24-dafa946c22af"
        ),
        "approval_decision_key": (
            "approval-decisions/"
            "f7807877-a08a-53b4-8e2b-a2ba89e9dd96/"
            "0e51ed68-090b-4ded-8c24-dafa946c22af/"
            "approved.json"
        ),
        "decision": "APPROVED",
        "decided_by": "test-reviewer",
        "response_mode": "DRY_RUN",
        "proposed_actions": [
            "Review DNS activity.",
            "Preserve relevant evidence.",
        ],
    }


class DryRunResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with SCHEMA_PATH.open(
            encoding="utf-8"
        ) as schema_file:
            schema = json.load(schema_file)

        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    def test_creates_non_executing_response(
        self,
    ) -> None:
        response = create_dry_run_response(
            valid_event(),
            now=datetime(
                2026,
                10,
                2,
                20,
                0,
                tzinfo=timezone.utc,
            ),
        )

        self.assertEqual(
            response["status"],
            "SIMULATED",
        )
        self.assertFalse(response["executed"])
        self.assertEqual(
            response["resource_changes"],
            0,
        )
        self.assertTrue(
            all(
                action["status"] == "NOT_EXECUTED"
                for action in response[
                    "simulated_actions"
                ]
            )
        )

    def test_response_matches_schema(self) -> None:
        response = create_dry_run_response(
            valid_event()
        )

        errors = sorted(
            self.validator.iter_errors(response),
            key=lambda error: list(error.path),
        )

        self.assertEqual(errors, [])

    def test_non_approved_decision_is_rejected(
        self,
    ) -> None:
        event = valid_event()
        event["decision"] = "REJECTED"

        with self.assertRaisesRegex(
            ValueError,
            "approved decision",
        ):
            create_dry_run_response(event)

    def test_live_response_mode_is_rejected(
        self,
    ) -> None:
        event = valid_event()
        event["response_mode"] = "LIVE"

        with self.assertRaisesRegex(
            ValueError,
            "DRY_RUN mode",
        ):
            create_dry_run_response(event)

    def test_persists_response_and_metadata(
        self,
    ) -> None:
        response = create_dry_run_response(
            valid_event()
        )
        s3_client = Mock()
        dynamodb_client = Mock()

        with patch.dict(
            "os.environ",
            {
                "EVIDENCE_BUCKET_NAME": "test-bucket",
                "INCIDENT_TABLE_NAME": "test-table",
            },
            clear=True,
        ):
            persistence = persist_dry_run_response(
                response,
                s3_client=s3_client,
                dynamodb_client=dynamodb_client,
            )

        s3_client.put_object.assert_called_once()
        s3_request = (
            s3_client.put_object.call_args.kwargs
        )

        self.assertEqual(
            s3_request["ServerSideEncryption"],
            "AES256",
        )

        stored_document = json.loads(
            s3_request["Body"]
        )
        self.assertFalse(
            stored_document["executed"]
        )

        dynamodb_client.update_item.assert_called_once()
        dynamodb_request = (
            dynamodb_client.update_item.call_args.kwargs
        )

        self.assertIn(
            "approval_status = :approved",
            dynamodb_request["ConditionExpression"],
        )
        self.assertFalse(
            dynamodb_request[
                "ExpressionAttributeValues"
            ][":executed"]["BOOL"]
        )
        self.assertEqual(
            persistence["response_status"],
            "SIMULATED",
        )

    @patch(
        "src.approval_workflow.dry_run_response."
        "persist_dry_run_response"
    )
    def test_lambda_handler_returns_response(
        self,
        persist_response: Mock,
    ) -> None:
        persist_response.return_value = {
            "response_status": "SIMULATED",
        }

        result = lambda_handler(
            valid_event(),
            None,
        )

        self.assertEqual(
            result["dry_run_response"]["response_mode"],
            "DRY_RUN",
        )
        persist_response.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)