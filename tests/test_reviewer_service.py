import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.reviewer_interface.service import (
    list_pending_approvals,
)
from src.reviewer_interface.service import (
    load_approval_request,
)
from src.reviewer_interface.service import (
    submit_decision,
)


def valid_request() -> dict:
    return {
        "schema_version": "1.0.0",
        "approval_id": (
            "504a1031-d4a8-486d-9cb0-3cf5e1936c92"
        ),
        "finding_id": (
            "493aa39f-cc70-57bc-be04-fcb475305e44"
        ),
        "investigation_key": (
            "ai-investigations/"
            "493aa39f-cc70-57bc-be04-fcb475305e44.json"
        ),
        "provider": "ollama",
        "model_id": "qwen3:14b",
        "summary": "Suspicious DNS activity.",
        "confidence": "HIGH",
        "proposed_actions": [
            "Review network telemetry.",
        ],
        "status": "PENDING",
        "requested_at": "2026-10-02T18:00:00Z",
        "expires_at": "2026-10-03T18:00:00Z",
        "requires_human_approval": True,
        "response_mode": "DRY_RUN",
    }


def pending_item(
    approval_id: str,
    requested_at: str,
) -> dict:
    return {
        "finding_id": {
            "S": "493aa39f-cc70-57bc-be04-fcb475305e44",
        },
        "approval_id": {
            "S": approval_id,
        },
        "approval_request_key": {
            "S": f"approval-requests/{approval_id}.json",
        },
        "approval_requested_at": {
            "S": requested_at,
        },
        "approval_expires_at": {
            "S": "2026-10-03T18:00:00Z",
        },
        "approval_response_mode": {
            "S": "DRY_RUN",
        },
    }


class ReviewerServiceTests(unittest.TestCase):
    def test_pending_approvals_are_sorted(
        self,
    ) -> None:
        client = Mock()
        client.scan.side_effect = [
            {
                "Items": [
                    pending_item(
                        "approval-002",
                        "2026-10-02T19:00:00Z",
                    ),
                ],
                "LastEvaluatedKey": {
                    "finding_id": {
                        "S": "page-key",
                    },
                },
            },
            {
                "Items": [
                    pending_item(
                        "approval-001",
                        "2026-10-02T18:00:00Z",
                    ),
                ],
            },
        ]

        approvals = list_pending_approvals(
            client,
            "test-table",
        )

        self.assertEqual(
            [
                item["approval_id"]
                for item in approvals
            ],
            [
                "approval-001",
                "approval-002",
            ],
        )
        self.assertEqual(
            client.scan.call_count,
            2,
        )

    def test_loads_safe_request_from_s3(
        self,
    ) -> None:
        client = Mock()
        client.get_object.return_value = {
            "Body": io.BytesIO(
                json.dumps(
                    valid_request()
                ).encode("utf-8")
            ),
        }

        request = load_approval_request(
            client,
            "test-bucket",
            "approval-requests/request.json",
        )

        self.assertEqual(
            request["response_mode"],
            "DRY_RUN",
        )

    def test_submit_decision_invokes_lambda(
        self,
    ) -> None:
        client = Mock()
        client.invoke.return_value = {
            "Payload": io.BytesIO(
                json.dumps(
                    {
                        "approval_decision": {
                            "decision": "APPROVED",
                            "response_mode": "DRY_RUN",
                        },
                        "persistence": {},
                    }
                ).encode("utf-8")
            ),
        }

        result = submit_decision(
            lambda_client=client,
            function_name="decision-function",
            approval_request=valid_request(),
            decision="approved",
            decided_by="reviewer",
            comment="Validated.",
        )

        invocation = client.invoke.call_args.kwargs
        payload = json.loads(invocation["Payload"])

        self.assertEqual(
            payload["decision"],
            "APPROVED",
        )
        self.assertEqual(
            result["approval_decision"]["response_mode"],
            "DRY_RUN",
        )

    def test_rejection_requires_comment(
        self,
    ) -> None:
        client = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "require a comment",
        ):
            submit_decision(
                lambda_client=client,
                function_name="decision-function",
                approval_request=valid_request(),
                decision="REJECTED",
                decided_by="reviewer",
                comment="",
            )

        client.invoke.assert_not_called()

    def test_unsafe_lambda_response_is_rejected(
        self,
    ) -> None:
        client = Mock()
        client.invoke.return_value = {
            "Payload": io.BytesIO(
                json.dumps(
                    {
                        "approval_decision": {
                            "decision": "APPROVED",
                            "response_mode": "LIVE",
                        }
                    }
                ).encode("utf-8")
            ),
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "unsafe mode",
        ):
            submit_decision(
                lambda_client=client,
                function_name="decision-function",
                approval_request=valid_request(),
                decision="APPROVED",
                decided_by="reviewer",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)