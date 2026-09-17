import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "ai-investigation.schema.json"
)


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


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


class AiInvestigationSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema = load_schema()
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)

    def test_valid_investigation_matches_schema(self) -> None:
        self.assertTrue(
            self.validator.is_valid(valid_investigation())
        )

    def test_human_approval_cannot_be_disabled(self) -> None:
        investigation = valid_investigation()
        investigation["requires_human_approval"] = False

        self.assertFalse(
            self.validator.is_valid(investigation)
        )

    def test_unknown_properties_are_rejected(self) -> None:
        investigation = valid_investigation()
        investigation["executed_action"] = "Instance isolated"

        self.assertFalse(
            self.validator.is_valid(investigation)
        )

    def test_unknown_schema_version_is_rejected(self) -> None:
        investigation = valid_investigation()
        investigation["schema_version"] = "2.0.0"

        self.assertFalse(
            self.validator.is_valid(investigation)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)