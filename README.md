# AI CloudSec Incident Responder Lab

A portfolio project that demonstrates an AI-assisted cloud security detection and incident-response workflow built on AWS.

## Project status

- **Completed:** Sprint 0 — Foundation; Sprint 1 — AWS Baseline
- **Current:** Sprint 2 — Detection Pipeline
- **Current progress:** Protected evidence storage, event ingestion, normalized finding schema, and EventBridge-to-Lambda routing are operational.
- **Next objective:** Persist normalized findings in Amazon S3 and DynamoDB.

## Objective

Build a secure and auditable pipeline that receives cloud-security findings, normalizes the evidence, uses generative AI to assist the investigation, and proposes response actions for human approval.

## Planned workflow

Synthetic GuardDuty finding → Amazon EventBridge → AWS Lambda → Amazon S3 and DynamoDB → Amazon Bedrock → Human approval

## Repository structure

- `docs/` — Architecture, setup notes, threat model, and project decisions.
- `infrastructure/` — Infrastructure-as-code definitions.
- `src/` — Python application and Lambda function code.
- `tests/` — Automated tests.
- `sample-events/` — Synthetic security findings with no sensitive data.

## Documentation

- [Project charter](docs/project-charter.md)
- [Environment setup notes](docs/setup-notes.md)
- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Sprint 0 retrospective](docs/sprint-0-retrospective.md)
- [Sprint 1 retrospective](docs/sprint-1-retrospective.md)
- [Terraform state design](docs/terraform-state.md)
- [Terraform deployment role design](docs/terraform-deployment-role.md)
- [EventBridge DLQ design](docs/eventbridge-dlq.md)

## Local validation

Activate the Python virtual environment and run the project validation script before committing changes:

```powershell
.\scripts\validate_project.ps1
```

The script validates the synthetic fixtures, normalized finding schema, Python unit tests, Terraform formatting and configuration, and Git whitespace.

## Security principles

- Least-privilege access
- No credentials or sensitive data in source control
- Evidence-based AI analysis
- Human approval before response actions
- Logging and auditability
- Cost-aware cloud deployment

## Known limitation

Amazon GuardDuty is restricted in the current AWS account. The lab will use synthetic GuardDuty-compatible findings delivered through EventBridge.

## Roadmap

1. Foundation and threat model
2. AWS security baseline
3. Detection pipeline
4. AI-assisted investigation
5. Human approval and portfolio demonstration
