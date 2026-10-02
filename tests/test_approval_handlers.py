import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.approval_workflow.handlers import (
    create_request_handler,
)
from src.approval_workflow.handlers import (
    record_decision_handler,
)


FINDING_ID = "493aa39f-cc70-57bc-be04-fcb475305e44"
APPROVAL_ID = "bfa87a11-ef45-4c1e-a9b0-40286ecf89c1"
INVESTIGATION_KEY = (
    f"ai-investigations/{FINDING_ID}.json"
)


def investigation_result() -> dict:
    return {
        "provider": "ollama",
        "model_id": "qwen3:14b",
        "investigation": {
            "summary": "A finding requires review.",
            "confidence": "MEDIUM",
            "recommended_actions": [
                "Review related activity.",
            ],
            "requires_human_approval": True,
        },
    }


def approval_request() -> dict:
    return {
        "approval_id": APPROVAL_ID,
        "finding_id": FINDING_ID,
        "investigation_key": INVESTIGATION_KEY,
        "status": "PENDING",
        "response_mode": "DRY_RUN",
        "requires_human_approval": True,
        "expires_at": "2099-10-02T22:30:00Z",
    }


class ApprovalHandlerTests(unittest.TestCase):
    @patch(
        "src.approval_workflow.handlers."
        "persist_approval_request"
    )
    @patch(
        "src.approval_workflow.handlers."
        "create_approval_request"
    )
    def test_create_request_handler(
        self,
        create_request,
        persist_request,
    ) -> None:
        request = approval_request()
        persistence = {
            "status": "PENDING",
        }

        create_request.return_value = request
        persist_request.return_value = persistence
        result_data = investigation_result()

        result = create_request_handler(
            {
                "finding_id": FINDING_ID,
                "investigation_key": INVESTIGATION_KEY,
                "approval_id": APPROVAL_ID,
                "investigation_result": result_data,
            },
            None,
        )

        create_request.assert_called_once_with(
            finding_id=FINDING_ID,
            result=result_data,
            investigation_key=INVESTIGATION_KEY,
            approval_id=APPROVAL_ID,
        )
        persist_request.assert_called_once_with(request)
        self.assertEqual(
            result["approval_request"],
            request,
        )

    @patch(
        "src.approval_workflow.handlers."
        "persist_approval_decision"
    )
    @patch(
        "src.approval_workflow.handlers."
        "create_approval_decision"
    )
    def test_record_decision_handler(
        self,
        create_decision,
        persist_decision,
    ) -> None:
        request = approval_request()
        decision = {
            "finding_id": FINDING_ID,
            "approval_id": APPROVAL_ID,
            "decision": "APPROVED",
            "response_mode": "DRY_RUN",
        }

        create_decision.return_value = decision
        persist_decision.return_value = {
            "decision": "APPROVED",
        }

        result = record_decision_handler(
            {
                "approval_request": request,
                "decision": "APPROVED",
                "decided_by": "reviewer@example.com",
            },
            None,
        )

        create_decision.assert_called_once_with(
            request=request,
            decision="APPROVED",
            decided_by="reviewer@example.com",
            comment=None,
        )
        persist_decision.assert_called_once_with(decision)
        self.assertEqual(
            result["approval_decision"],
            decision,
        )

    def test_request_handler_requires_approval_id(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "event.approval_id",
        ):
            create_request_handler(
                {
                    "finding_id": FINDING_ID,
                    "investigation_key": (
                        INVESTIGATION_KEY
                    ),
                    "investigation_result": (
                        investigation_result()
                    ),
                },
                None,
            )

    def test_decision_handler_requires_request(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "event.approval_request",
        ):
            record_decision_handler(
                {
                    "decision": "APPROVED",
                    "decided_by": (
                        "reviewer@example.com"
                    ),
                },
                None,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)