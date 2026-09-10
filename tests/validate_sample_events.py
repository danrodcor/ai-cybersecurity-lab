import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "normalized-finding.schema.json"
SAMPLE_PATH = PROJECT_ROOT / "sample-events" / "normalized-finding.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def format_error_path(error) -> str:
    if not error.absolute_path:
        return "<root>"

    return ".".join(str(part) for part in error.absolute_path)


def main() -> None:
    schema = load_json(SCHEMA_PATH)
    sample = load_json(SAMPLE_PATH)

    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(sample),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        print(f"FAIL: {SAMPLE_PATH.relative_to(PROJECT_ROOT)}")
        for error in errors:
            print(f"- {format_error_path(error)}: {error.message}")

        raise SystemExit(1)

    print(
        "PASS: "
        f"{SAMPLE_PATH.relative_to(PROJECT_ROOT)} matches "
        f"{SCHEMA_PATH.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()