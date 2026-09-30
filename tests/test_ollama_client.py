import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_investigator.ollama_client import invoke_ollama
from src.ai_investigator.ollama_client import (
    load_investigation_schema,
)


def ollama_api_response() -> dict:
    return {
        "model": "qwen3:14b",
        "message": {
            "role": "assistant",
            "content": json.dumps(
                {
                    "schema_version": "1.0.0",
                    "summary": "Synthetic investigation.",
                    "confidence": "HIGH",
                    "observed_facts": [
                        "A synthetic DNS request occurred.",
                    ],
                    "hypotheses": [],
                    "recommended_actions": [
                        "Review the synthetic evidence.",
                    ],
                    "requires_human_approval": True,
                }
            ),
        },
        "prompt_eval_count": 120,
        "eval_count": 55,
        "done_reason": "stop",
    }


def mock_transport(
    api_response: dict,
) -> Mock:
    response = MagicMock()
    response.read.return_value = json.dumps(
        api_response
    ).encode("utf-8")

    transport = MagicMock()
    transport.return_value.__enter__.return_value = (
        response
    )

    return transport


class OllamaClientTests(unittest.TestCase):
    def test_schema_enforces_human_approval(
        self,
    ) -> None:
        schema = load_investigation_schema()

        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "1.0.0",
        )
        self.assertIs(
            schema["properties"][
                "requires_human_approval"
            ]["const"],
            True,
        )

    def test_invoke_ollama_uses_structured_local_request(
        self,
    ) -> None:
        transport = mock_transport(
            ollama_api_response()
        )

        result = invoke_ollama(
            prompt="Investigate synthetic evidence.",
            system_prompt="Require human approval.",
            model_id="qwen3:14b",
            transport=transport,
        )

        transport.assert_called_once()
        request = transport.call_args.args[0]
        request_payload = json.loads(
            request.data.decode("utf-8")
        )

        self.assertEqual(
            request.full_url,
            "http://localhost:11434/api/chat",
        )
        self.assertFalse(
            request_payload["stream"]
        )
        self.assertFalse(
            request_payload["think"]
        )
        self.assertEqual(
            request_payload["options"]["temperature"],
            0,
        )
        self.assertEqual(
            request_payload["format"]["type"],
            "object",
        )
        self.assertEqual(
            result["provider"],
            "ollama",
        )
        self.assertEqual(
            result["model_id"],
            "qwen3:14b",
        )
        self.assertEqual(
            result["usage"]["total_tokens"],
            175,
        )
        self.assertEqual(
            result["stop_reason"],
            "stop",
        )

    def test_remote_endpoint_is_rejected(
        self,
    ) -> None:
        transport = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "must use local HTTP",
        ):
            invoke_ollama(
                prompt="Synthetic evidence.",
                system_prompt="Safe investigation.",
                model_id="qwen3:14b",
                endpoint="https://example.com/api/chat",
                transport=transport,
            )

        transport.assert_not_called()

    def test_missing_model_id_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "model_id",
        ):
            invoke_ollama(
                prompt="Synthetic evidence.",
                system_prompt="Safe investigation.",
                model_id=" ",
                transport=Mock(),
            )

    def test_invalid_api_response_is_rejected(
        self,
    ) -> None:
        transport = mock_transport(
            {
                "model": "qwen3:14b",
                "message": {},
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "valid text output",
        ):
            invoke_ollama(
                prompt="Synthetic evidence.",
                system_prompt="Safe investigation.",
                model_id="qwen3:14b",
                transport=transport,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)