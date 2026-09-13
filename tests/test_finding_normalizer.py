import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema import FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.finding_normalizer.handler import normalize_finding


SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "normalized-finding.schema.json"
)

FIXTURES = {
    "guardduty-finding-high.json": "HIGH",
    "guardduty-finding-medium.json": "MEDIUM",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


class FindingNormalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema = load_json(SCHEMA_PATH)

        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    def test_fixtures_match_normalized_schema(self) -> None:
        for filename, expected_label in FIXTURES.items():
            with self.subTest(filename=filename):
                fixture_path = (
                    PROJECT_ROOT
                    / "sample-events"
                    / filename
                )
                event = load_json(fixture_path)
                normalized = normalize_finding(event)

                errors = sorted(
                    self.validator.iter_errors(normalized),
                    key=lambda error: list(error.path),
                )

                messages = [
                    (
                        f"{'.'.join(map(str, error.path)) or '<root>'}: "
                        f"{error.message}"
                    )
                    for error in errors
                ]

                self.assertEqual(
                    messages,
                    [],
                    msg="\n".join(messages),
                )

                self.assertEqual(
                    normalized["severity"]["label"],
                    expected_label,
                )
                self.assertEqual(
                    normalized["source"]["finding_id"],
                    event["detail"]["id"],
                )
                self.assertEqual(
                    normalized["account_id"],
                    event["detail"]["accountId"],
                )
                self.assertEqual(
                    normalized["region"],
                    event["detail"]["region"],
                )
                self.assertTrue(normalized["synthetic"])

    def test_normalized_id_is_deterministic(self) -> None:
        fixture_path = (
            PROJECT_ROOT
            / "sample-events"
            / "guardduty-finding-high.json"
        )
        event = load_json(fixture_path)

        first_result = normalize_finding(event)
        second_result = normalize_finding(event)

        self.assertEqual(
            first_result["finding_id"],
            second_result["finding_id"],
        )

    def test_unsupported_source_is_rejected(self) -> None:
        fixture_path = (
            PROJECT_ROOT
            / "sample-events"
            / "guardduty-finding-high.json"
        )
        event = load_json(fixture_path)
        event["source"] = "untrusted.example"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported event source",
        ):
            normalize_finding(event)


if __name__ == "__main__":
    unittest.main(verbosity=2)