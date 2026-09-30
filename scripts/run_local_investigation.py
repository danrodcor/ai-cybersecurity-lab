"""Run a safe AI investigation with local Ollama."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_investigator.investigator import (
    investigate_finding_locally,
)

from src.ai_investigator.persistence import (
    persist_investigation,
)

def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON document."""
    with path.open(encoding="utf-8") as json_file:
        document = json.load(json_file)

    if not isinstance(document, dict):
        raise ValueError(
            "Finding document must be a JSON object"
        )

    return document


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Investigate one normalized finding "
            "with a local Ollama model."
        )
    )
    parser.add_argument(
        "finding_path",
        type=Path,
        help="Path to one normalized finding JSON file.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help=(
            "Local Ollama model identifier. "
            "Defaults to OLLAMA_MODEL_ID or qwen3:14b."
        ),
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help=(
            "Persist the validated investigation "
            "to the configured AWS resources."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Run one local investigation."""
    arguments = parse_arguments()
    finding = load_json(
        arguments.finding_path
    )

    result = investigate_finding_locally(
        finding,
        model_id=arguments.model_id,
    )

    if arguments.persist:
        result["persistence"] = persist_investigation(
            finding_id=finding.get("finding_id", ""),
            result=result,
        )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())