# AI CloudSec Incident Responder Lab

A portfolio project that demonstrates an AI-assisted cloud security detection and incident-response workflow built on AWS.

## Project status

Sprint 0 — Foundation

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
