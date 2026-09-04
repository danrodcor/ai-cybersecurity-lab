# Threat Model

## Purpose

This threat model identifies the primary security risks in the AI-assisted
incident-response pipeline and documents the controls used to reduce them.

The model follows the STRIDE methodology and should be reviewed whenever the
architecture, trust boundaries, permissions, or automated actions change.

## Scope

The following components are in scope:

- Synthetic GuardDuty-compatible findings
- Amazon EventBridge
- Finding normalizer Lambda
- DynamoDB incident metadata
- S3 evidence storage
- Evidence collector
- Amazon Bedrock investigation
- Output validation
- AWS Step Functions approval workflow
- Human reviewer and dry-run response actions
- Audit logs

See [Architecture](architecture.md) for the system diagram and data flows.

## Security objectives

- Accept findings only from trusted and identifiable sources.
- Preserve the integrity of findings, evidence, and investigation results.
- Prevent sensitive evidence from reaching the AI model unnecessarily.
- Keep AI-generated content from directly triggering response actions.
- Maintain an auditable record of every important decision and state change.
- Limit every component to the minimum permissions it requires.

## STRIDE analysis

| ID | Category | Component | Threat | Potential impact | Primary mitigations | Residual risk |
|---|---|---|---|---|---|---|
| TM-01 | Spoofing | EventBridge input | An attacker or unauthorized principal submits a forged GuardDuty-compatible finding. | False incidents could consume resources or influence an investigation. | Restrict `PutEvents` permissions, validate the event source and schema, and record the submitting principal through CloudTrail. | A compromised authorized principal could still submit believable false events. |
| TM-02 | Tampering | S3 and DynamoDB | Findings, evidence, or incident metadata are modified after collection. | The investigation could reach incorrect conclusions or lose forensic reliability. | Enable S3 versioning and encryption, restrict write permissions, use DynamoDB encryption, and record access through audit logs. | Authorized processes with write access could introduce incorrect data. |
| TM-03 | Repudiation | Approval workflow | A user denies approving, rejecting, or modifying a proposed response action. | The organization may be unable to reconstruct accountability during an investigation. | Record reviewer identity, timestamp, decision, workflow execution ID, and proposed action in durable audit logs. | Administrators with access to logging systems may still attempt to alter records. |
| TM-04 | Information Disclosure | Evidence collector and Bedrock | Secrets, credentials, personal data, or unrelated evidence are included in the model prompt. | Sensitive information could be exposed beyond its intended processing boundary. | Use an allow-list of evidence fields, redact sensitive values, minimize prompt contents, encrypt data, and avoid storing secrets in findings. | Sensitive information may appear inside an otherwise approved field. |
| TM-05 | Denial of Service | EventBridge and Lambda | A large volume of synthetic or malicious findings overwhelms processing or increases cost. | Delayed investigations, Lambda throttling, queue growth, or unexpected AWS charges. | Apply rate limits, concurrency limits, retry controls, dead-letter handling, monitoring, and the USD 15 monthly budget alert. | A sustained event spike may still delay legitimate investigations. |
| TM-06 | Elevation of Privilege | Lambda and Step Functions roles | A compromised function uses excessive IAM permissions to access evidence or invoke response actions. | Unauthorized access or actions could affect resources outside the incident scope. | Use separate least-privilege roles, restrict resources and actions, avoid wildcard permissions, and keep all response actions in dry-run mode. | Misconfigured policies could unintentionally grant broader access. |
| TM-07 | Tampering | Bedrock output | Prompt injection contained in evidence manipulates the model's conclusions or proposed actions. | The model could produce misleading analysis or unsafe recommendations. | Treat evidence as untrusted data, use explicit prompt boundaries, require structured JSON, validate output, and require human approval. | Model behavior cannot be made completely deterministic. |

## Trust-boundary rules

1. Events crossing into the detection pipeline must be authenticated and
   schema-validated.
2. Evidence must be treated as untrusted input even when it comes from an
   approved AWS service.
3. Only allow-listed evidence may cross into the AI processing boundary.
4. Bedrock output is advisory and must never be treated as an authorization
   decision.
5. Every proposed response action requires validation and explicit human
   approval.
6. The current laboratory supports dry-run actions only.

## Review triggers

Review and update this threat model when:

- A new AWS service or data store is added.
- IAM permissions or trust relationships change.
- The evidence schema changes.
- A real GuardDuty integration replaces synthetic findings.
- The project permits actions beyond dry-run mode.
- A new threat or security test reveals an undocumented risk.