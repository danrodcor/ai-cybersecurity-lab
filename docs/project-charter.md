# Project Charter

## Project name

AI CloudSec Incident Responder Lab

## Problem statement

Cloud-security findings often require analysts to collect evidence, determine severity, document conclusions, and propose response actions under time pressure.

This project will demonstrate how AWS serverless services and generative AI can assist that workflow while preserving human oversight, auditability, and cost control.

## Goal

Build a secure, reproducible, and portfolio-ready prototype that receives a synthetic cloud-security finding, normalizes and stores its evidence, uses Amazon Bedrock to produce a structured investigation, and proposes a response for human approval.

## Objectives

- Build the infrastructure through Terraform.
- Receive synthetic GuardDuty-compatible findings through Amazon EventBridge.
- Normalize findings with AWS Lambda.
- Store incident metadata and evidence securely.
- Use Amazon Bedrock for evidence-grounded investigation assistance.
- Validate AI output before accepting it.
- Require human approval before any simulated containment action.
- Preserve logs and evidence for auditing.
- Document the architecture, threats, controls, tests, and results.

## In scope

- Amazon EventBridge
- AWS Lambda
- Amazon S3
- Amazon DynamoDB
- Amazon Bedrock
- AWS Step Functions
- Amazon CloudWatch
- AWS Identity and Access Management
- Terraform
- Python
- Synthetic security findings
- Automated tests and security documentation

## Out of scope

- Production workloads or production data
- Autonomous containment actions
- Real malware execution
- Live GuardDuty integration in the restricted account
- Multi-account or multi-region deployment
- A production SOC platform
- A full graphical user interface
- Continuous high-volume event processing

## Cost ceiling

The project has a monthly AWS operating ceiling of USD 15.

Cost controls:

- Use the existing AWS Budget and cost anomaly monitor.
- Treat budget notifications as alerts, not as a guaranteed spending stop.
- Prefer serverless and pay-per-use services.
- Avoid continuously running compute, databases, NAT gateways, and search clusters.
- Remove temporary resources after testing.
- Review estimated cost before every deployment.
- Stop new deployments and investigate if actual or forecasted spend approaches USD 15.

## Security guardrails

- Never commit passwords, access keys, tokens, account identifiers, or sensitive data.
- Use least-privilege IAM permissions.
- Encrypt stored evidence.
- Block public access to storage.
- Use only synthetic test data.
- Validate and constrain all AI-generated output.
- Treat AI recommendations as untrusted until reviewed.
- Require human approval before response actions.
- Preserve relevant logs for investigation and audit.
- Review Terraform plans before applying changes.

## Deliverables

- Terraform configuration
- Synthetic GuardDuty-compatible event samples
- Finding-normalization Lambda function
- Automated unit tests
- Evidence storage design
- Bedrock investigation workflow
- Human-approval workflow
- Architecture diagram
- Threat model
- Security and cost review
- Portfolio case study

## Success criteria

The project is successful when:

1. Terraform formatting and validation complete without errors.
2. A synthetic finding reaches the processing pipeline.
3. Lambda converts the finding into the documented internal schema.
4. Incident metadata and evidence are stored securely.
5. Bedrock returns a valid structured investigation based only on supplied evidence.
6. Invalid or unsafe AI output is rejected safely.
7. A response recommendation reaches a human-approval step.
8. No containment action executes automatically.
9. No secrets or sensitive data are present in the repository.
10. Total monthly AWS cost remains at or below USD 15.
11. Another technical reviewer can understand and reproduce the prototype from the documentation.

## Constraints and assumptions

- GuardDuty is unavailable in the current AWS account.
- Synthetic GuardDuty-compatible events will replace live findings.
- The repository is public and must contain no sensitive information.
- The project is developed by one person on Windows.
- Sessions normally last approximately 45 minutes.
- The laboratory is educational and portfolio-oriented, not production-ready.