import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_investigator.evidence_collector import collect_evidence


FIXTURE_PATH = (
    PROJECT_ROOT
    / "sample-events"
    / "normalized-finding.json"
)


def load_finding() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as json_file:
        return json.load(json_file)


class EvidenceCollectorTests(unittest.TestCase):
    def test_collector_preserves_required_evidence(
        self,
    ) -> None:
        evidence = collect_evidence(load_finding())

        self.assertEqual(
            evidence["finding_id"],
            "7f3fbec2-cf2a-4de7-9125-e345cd68c02f",
        )
        self.assertEqual(
            evidence["finding_type"],
            (
                "UnauthorizedAccess:IAMUser/"
                "ConsoleLoginSuccess.B"
            ),
        )
        self.assertEqual(
            evidence["severity"]["label"],
            "HIGH",
        )
        self.assertEqual(
            evidence["actor"]["source_ip"],
            "198.51.100.24",
        )
        self.assertEqual(
            evidence["threat"]["technique_id"],
            "T1078",
        )

    def test_collector_removes_sensitive_identifiers(
        self,
    ) -> None:
        evidence = collect_evidence(load_finding())

        self.assertNotIn("account_id", evidence)
        self.assertNotIn("finding_id", evidence["source"])
        self.assertNotIn("id", evidence["resource"])
        self.assertNotIn("arn", evidence["resource"])
        self.assertNotIn(
            "account_id",
            evidence["resource"],
        )
        self.assertNotIn(
            "principal_id",
            evidence["actor"],
        )

    def test_collector_enforces_size_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "exceeds the size limit",
        ):
            collect_evidence(
                load_finding(),
                max_bytes=10,
            )

    def test_collector_requires_valid_limit(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "positive integer",
        ):
            collect_evidence(
                load_finding(),
                max_bytes=0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)