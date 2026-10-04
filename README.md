# AI CloudSec Incident Responder Lab

A portfolio project that demonstrates an AI-assisted cloud security detection and incident-response workflow built on AWS.

## Project status

- **Completed:** Sprint 0 — Foundation; Sprint 1 — AWS Baseline; Sprint 2 — Detection Pipeline; Sprint 3 — AI Investigation
- **Current:** Sprint 4 — Approval & Portfolio
- **Current progress:** Native and synthetic GuardDuty findings are normalized and investigated locally with Qwen3 14B through Ollama. Validated investigations enter a Streamlit and AWS Step Functions approval workflow with tested `APPROVED`, `REJECTED`, and `EXPIRED` branches. Approved actions invoke a dry-run Lambda that performs zero resource changes.
- **Next objective:** Complete the security and cost review, capture final demonstration evidence, and write the portfolio case study.

## Objective

Build a secure and auditable pipeline that receives cloud-security findings, normalizes the evidence, uses generative AI to assist the investigation, and proposes response actions for human approval.

## Implemented workflow

GuardDuty finding → EventBridge → finding-normalizer Lambda → Amazon S3 and DynamoDB → local Ollama investigation → schema validation → Streamlit reviewer and AWS Step Functions → dry-run response Lambda → audit trail

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
- [Approval workflow validation](docs/approval-workflow-validation.md)
- [Security and cost review](docs/security-cost-review.md)
- [Threat model](docs/threat-model.md)
- [Sprint 0 retrospective](docs/sprint-0-retrospective.md)
- [Sprint 1 retrospective](docs/sprint-1-retrospective.md)
- [Terraform state design](docs/terraform-state.md)
- [Terraform deployment role design](docs/terraform-deployment-role.md)
- [EventBridge DLQ design](docs/eventbridge-dlq.md)
- [End-to-end demo walkthrough](docs/demo-walkthrough.md)
- [Portfolio case study](docs/portfolio-case-study.md)


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

Amazon Bedrock inference quotas remain unavailable for this AWS account. The lab therefore uses local Qwen3 14B through Ollama as its active model provider while retaining the Bedrock adapter for future use. Amazon GuardDuty is enabled in `us-east-1` with cost-controlled foundational protection.

## Roadmap

1. Foundation and threat model
2. AWS security baseline
3. Detection pipeline
4. AI-assisted investigation
5. Human approval and portfolio demonstration
