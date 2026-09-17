import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_investigator.investigator import investigate_finding
from src.ai_investigator.investigator import parse_investigation_response


def valid_investigation() -> dict:
    return {
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
    }


def bedrock_response(
    investigation: dict | None = None,
) -> dict:
    return {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps(
                            investigation
                            or valid_investigation()
                        ),
                    }
                ],
            }
        },
        "usage": {
            "inputTokens": 250,
            "outputTokens": 80,
            "totalTokens": 330,
        },
        "stopReason": "end_turn",
    }


class AiInvestigatorTests(unittest.TestCase):
    def test_investigate_finding_calls_converse(
        self,
    ) -> None:
        client = Mock()
        client.converse.return_value = bedrock_response()
        finding = {
            "finding_id": "finding-001",
            "severity": {
                "label": "HIGH",
            },
        }

        result = investigate_finding(
            finding,
            bedrock_client=client,
            model_id="amazon.nova-micro-v1:0",
        )

        client.converse.assert_called_once()
        request = client.converse.call_args.kwargs

        self.assertEqual(
            request["modelId"],
            "amazon.nova-micro-v1:0",
        )
        self.assertEqual(
            request["inferenceConfig"]["temperature"],
            0.0,
        )
        self.assertIn(
            "explicit human approval",
            request["system"][0]["text"],
        )
        self.assertEqual(
            result["investigation"]["confidence"],
            "HIGH",
        )
        self.assertEqual(
            result["usage"]["totalTokens"],
            330,
        )
        self.assertEqual(
            result["stop_reason"],
            "end_turn",
        )

    def test_model_id_can_come_from_environment(
        self,
    ) -> None:
        client = Mock()
        client.converse.return_value = bedrock_response()

        with patch.dict(
            "os.environ",
            {
                "BEDROCK_MODEL_ID": "configured-model",
            },
            clear=True,
        ):
            result = investigate_finding(
                {
                    "finding_id": "finding-002",
                },
                bedrock_client=client,
            )

        self.assertEqual(
            result["model_id"],
            "configured-model",
        )

    def test_missing_model_configuration_is_rejected(
        self,
    ) -> None:
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "BEDROCK_MODEL_ID",
            ):
                investigate_finding(
                    {
                        "finding_id": "finding-003",
                    },
                    bedrock_client=Mock(),
                )

    def test_non_json_response_is_rejected(self) -> None:
        response = bedrock_response()
        response["output"]["message"]["content"][0][
            "text"
        ] = "not-json"

        with self.assertRaisesRegex(
            ValueError,
            "not valid JSON",
        ):
            parse_investigation_response(response)

    def test_unsupported_schema_version_is_rejected(
        self,
    ) -> None:
        investigation = valid_investigation()
        investigation["schema_version"] = "2.0.0"

        with self.assertRaisesRegex(
            ValueError,
            "unsupported schema version",
        ):
            parse_investigation_response(
                bedrock_response(investigation)
            )


    def test_response_cannot_bypass_human_approval(
        self,
    ) -> None:
        investigation = valid_investigation()
        investigation["requires_human_approval"] = False

        with self.assertRaisesRegex(
            ValueError,
            "must require human approval",
        ):
            parse_investigation_response(
                bedrock_response(investigation)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)