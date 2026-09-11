import ipaddress
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_EVENTS = PROJECT_ROOT / "sample-events"

FIXTURES = {
    "guardduty-finding-high.json": {
        "minimum_severity": 7.0,
        "maximum_severity": 8.9,
    },
    "guardduty-finding-medium.json": {
        "minimum_severity": 4.0,
        "maximum_severity": 6.9,
    },
}

REQUIRED_EVENT_FIELDS = {
    "version",
    "id",
    "detail-type",
    "source",
    "account",
    "time",
    "region",
    "resources",
    "detail",
}

REQUIRED_DETAIL_FIELDS = {
    "schemaVersion",
    "accountId",
    "region",
    "partition",
    "id",
    "arn",
    "type",
    "resource",
    "service",
    "severity",
    "createdAt",
    "updatedAt",
    "title",
    "description",
}

DOCUMENTATION_ACCOUNT = "111122223333"
DOCUMENTATION_NETWORK = ipaddress.ip_network("203.0.113.0/24")


def require_fields(data: dict, required: set[str], location: str) -> None:
    missing = sorted(required - data.keys())

    if missing:
        raise ValueError(
            f"{location} is missing required fields: {', '.join(missing)}"
        )


def validate_fixture(filename: str, severity_range: dict) -> str:
    fixture_path = SAMPLE_EVENTS / filename

    with fixture_path.open(encoding="utf-8") as fixture_file:
        event = json.load(fixture_file)

    require_fields(event, REQUIRED_EVENT_FIELDS, filename)

    if event["version"] != "0":
        raise ValueError(f"{filename}: version must be '0'")

    if event["source"] != "com.danrodcor.securitylab.guardduty":
        raise ValueError(f"{filename}: unexpected synthetic event source")

    if event["detail-type"] != "Synthetic GuardDuty Finding":
        raise ValueError(f"{filename}: unexpected detail-type")

    if event["account"] != DOCUMENTATION_ACCOUNT:
        raise ValueError(f"{filename}: use only the documentation account ID")

    if event["region"] != "us-east-1":
        raise ValueError(f"{filename}: expected region us-east-1")

    if not event["resources"]:
        raise ValueError(f"{filename}: resources must not be empty")

    detail = event["detail"]
    require_fields(detail, REQUIRED_DETAIL_FIELDS, f"{filename} detail")

    if detail["accountId"] != event["account"]:
        raise ValueError(f"{filename}: account values do not match")

    if detail["region"] != event["region"]:
        raise ValueError(f"{filename}: region values do not match")

    if detail["partition"] != "aws":
        raise ValueError(f"{filename}: unexpected AWS partition")

    severity = detail["severity"]

    if not isinstance(severity, (int, float)):
        raise ValueError(f"{filename}: severity must be numeric")

    minimum = severity_range["minimum_severity"]
    maximum = severity_range["maximum_severity"]

    if not minimum <= severity <= maximum:
        raise ValueError(
            f"{filename}: severity {severity} is outside "
            f"the expected range {minimum}-{maximum}"
        )

    service = detail["service"]
    additional_info = service.get("additionalInfo", {})

    if additional_info.get("sample") is not True:
        raise ValueError(f"{filename}: sample must be true")

    if additional_info.get("synthetic") is not True:
        raise ValueError(f"{filename}: synthetic must be true")

    resource = detail["resource"]

    if resource.get("resourceType") != "Instance":
        raise ValueError(f"{filename}: expected an EC2 Instance resource")

    instance_details = resource.get("instanceDetails", {})
    network_interfaces = instance_details.get("networkInterfaces", [])

    if not network_interfaces:
        raise ValueError(f"{filename}: networkInterfaces must not be empty")

    public_ip = network_interfaces[0].get("publicIp")

    if not public_ip:
        raise ValueError(f"{filename}: synthetic public IP is missing")

    if ipaddress.ip_address(public_ip) not in DOCUMENTATION_NETWORK:
        raise ValueError(
            f"{filename}: public IP must use the 203.0.113.0/24 "
            "documentation network"
        )

    action = service.get("action", {})
    dns_action = action.get("dnsRequestAction", {})
    domain = dns_action.get("domain", "")

    if not domain.endswith(".example"):
        raise ValueError(
            f"{filename}: DNS domain must use the reserved .example suffix"
        )

    return (
        f"PASS: {filename} is a safe synthetic GuardDuty fixture "
        f"with severity {severity}"
    )


def main() -> None:
    finding_ids: set[str] = set()

    for filename, severity_range in FIXTURES.items():
        message = validate_fixture(filename, severity_range)

        fixture_path = SAMPLE_EVENTS / filename
        with fixture_path.open(encoding="utf-8") as fixture_file:
            finding_id = json.load(fixture_file)["detail"]["id"]

        if finding_id in finding_ids:
            raise ValueError(f"{filename}: duplicate finding ID {finding_id}")

        finding_ids.add(finding_id)
        print(message)


if __name__ == "__main__":
    main()