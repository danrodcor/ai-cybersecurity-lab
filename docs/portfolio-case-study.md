# AI CloudSec Incident Responder — Portfolio Case Study

## Overview

The AI CloudSec Incident Responder is a security-engineering portfolio project that demonstrates how cloud-security findings can be normalized, investigated with generative AI, reviewed by a human, and passed to a controlled response workflow.

The project combines AWS security services, infrastructure as code, local AI inference, structured validation, and auditable human approval.

No production containment actions are performed. Every approved response remains in `DRY_RUN` mode and records zero resource changes.

## Problem

Cloud-security findings often contain inconsistent structures, incomplete context, and more information than an analyst needs for an initial investigation.

Introducing generative AI creates additional risks:

- Sensitive evidence may be exposed to a model.
- Prompt injection may be embedded in untrusted finding data.
- The model may invent unsupported conclusions.
- Invalid or unsafe output may be accepted by downstream systems.
- Automated response actions may execute without human authorization.
- Investigation and response activity may lack a reliable audit trail.

The project was designed to address these risks while remaining practical, inexpensive, and suitable for a personal AWS environment.

## Objectives

The implementation needed to:

- Accept native and synthetic GuardDuty findings.
- Normalize findings into a versioned internal contract.
- Preserve evidence in encrypted AWS storage.
- Send only allow-listed evidence to the AI model.
- Require structured AI output.
- Reject invalid or unsafe model responses.
- Require explicit human approval before response.
- Support approved, rejected, and expired workflow branches.
- Simulate response actions without changing AWS resources.
- Maintain an auditable record of every workflow stage.
- Remain within a small monthly AWS budget.

## Architecture

The workflow uses the following stages:

1. Amazon GuardDuty or a synthetic fixture produces a security finding.
2. Amazon EventBridge routes the event to a normalizer Lambda.
3. The Lambda validates and normalizes the finding.
4. Amazon S3 stores normalized evidence.
5. Amazon DynamoDB stores incident metadata.
6. A local investigation runner creates an allow-listed evidence package.
7. Qwen3 14B analyzes the evidence through Ollama.
8. The application validates the structured model response.
9. AWS Step Functions coordinates human approval.
10. A local Streamlit interface records the reviewer’s decision.
11. Approved requests invoke a dry-run response Lambda.
12. Rejected and expired requests close without invoking a response.
13. S3, DynamoDB, CloudWatch, and Step Functions preserve the audit trail.

Detailed design information is available in the [architecture document](architecture.md).

## Technology stack

| Area | Technology |
|---|---|
| Cloud platform | AWS |
| Infrastructure as code | Terraform |
| Security findings | Amazon GuardDuty |
| Event routing | Amazon EventBridge |
| Compute | AWS Lambda with Python 3.13 |
| Evidence storage | Amazon S3 |
| Incident metadata | Amazon DynamoDB |
| Workflow orchestration | AWS Step Functions |
| Local AI runtime | Ollama |
| Model | Qwen3 14B |
| Reviewer interface | Streamlit |
| Logging | Amazon CloudWatch |
| Audit support | AWS CloudTrail and Step Functions history |
| Testing | Python `unittest` and JSON Schema |
| Source control | Git and GitHub |

## Security design

### Untrusted input

GuardDuty events and synthetic fixtures are treated as untrusted input.

The normalizer validates required fields, accepted sources, severity values, resource details, and supported event types before producing the internal finding contract.

### Evidence minimization

The AI model does not receive the complete source event.

An evidence collector builds a size-limited allow-list containing only the fields required for investigation. Sensitive identifiers excluded by policy do not enter the model prompt.

### Prompt-injection resistance

Finding values are explicitly labeled as untrusted evidence rather than instructions.

The prompt requires the model to:

- Separate observed facts from hypotheses.
- Avoid inventing missing evidence.
- Return JSON only.
- Never claim that a response action was executed.
- Require human approval for every proposed action.

### Structured output validation

AI output is treated as untrusted.

The response must satisfy a versioned JSON contract containing:

- Schema version
- Summary
- Confidence
- Observed facts
- Hypotheses
- Recommended actions
- Human-approval requirement

Responses with invalid JSON, unsupported schema versions, invalid confidence values, malformed lists, or a disabled approval requirement are rejected.

### Human approval

AWS Step Functions manages three terminal outcomes:

- `APPROVED`
- `REJECTED`
- `EXPIRED`

Approval decisions include the reviewer identity, decision time, optional comment, and response mode.

Conditional DynamoDB updates prevent an expired workflow from overwriting an approval that has already been completed.

### Safe response boundary

Only approved requests can invoke the response Lambda.

The Lambda produces a simulated response record with:

```text
response_mode: DRY_RUN
status: SIMULATED
executed: false
resource_changes: 0
```

The implementation does not isolate instances, modify security groups, revoke credentials, or delete resources.

## Cost controls

The project uses several controls to limit AWS spending:

- USD 15 monthly AWS budget
- DynamoDB on-demand billing
- Lambda functions configured with 128 MB memory
- Lambda timeouts limited to 10 seconds
- CloudWatch log retention limited to 14 days
- Cost-controlled GuardDuty configuration
- Local AI inference through Ollama
- No provisioned model capacity
- No automated production containment resources

The complete assessment is available in the [security and cost review](security-cost-review.md).

## Engineering challenges

### Amazon Bedrock quotas

The original design used Amazon Bedrock for model inference.

The AWS account received zero inference quotas for the evaluated models, and the requested quota increase was not approved because of the account’s limited usage history.

Instead of blocking the project, the investigation layer was adapted to support local Ollama inference while retaining the Bedrock provider adapter for possible future use.

This preserved the security contracts and workflow design without introducing external inference cost.

### GuardDuty availability

GuardDuty was initially unavailable in the account, so the detection pipeline was built and tested with safe GuardDuty-compatible synthetic fixtures.

When GuardDuty became available, foundational detection was enabled and routed through the same normalizer. AWS-generated sample findings were explicitly classified as synthetic evidence.

### Approval expiration consistency

Initial testing showed that an expired Step Functions execution reached the correct terminal state but left the corresponding DynamoDB approval status as `PENDING`.

The workflow was corrected by adding a conditional DynamoDB update to the expiration branch. Retesting confirmed that both the workflow and stored incident state now finish as `EXPIRED`.

## Validation

The project includes automated tests for:

- Finding normalization
- Synthetic fixture safety
- Evidence collection
- Prompt construction
- Bedrock and Ollama provider behavior
- AI investigation schema validation
- Investigation persistence
- Approval request construction
- Approval request persistence
- Approval decision construction
- Approval decision persistence
- Dry-run response behavior
- Reviewer service behavior
- Approval JSON contracts

The validation script also checks:

- Terraform formatting
- Terraform configuration
- Unstaged Git whitespace
- Staged Git whitespace

The approved, rejected, and expired workflow branches were validated end to end.

Detailed results are available in:

- [Approval workflow validation](approval-workflow-validation.md)
- [End-to-end demo walkthrough](demo-walkthrough.md)

## Results

The completed implementation demonstrates:

- Native and synthetic GuardDuty ingestion
- Deterministic finding normalization
- Encrypted and versioned evidence storage
- Recoverable incident metadata
- Local evidence-grounded AI investigation
- Provider-aware result persistence
- Strict JSON and safety validation
- Human approval through a local interface
- Step Functions workflow orchestration
- Approved, rejected, and expired terminal states
- Simulated response with zero resource changes
- Centralized logs and auditable evidence

## Skills demonstrated

This project demonstrates practical experience with:

- AWS security architecture
- Cloud detection pipelines
- Event-driven design
- IAM and least privilege
- Terraform
- Python
- Lambda
- EventBridge
- GuardDuty
- S3 and DynamoDB
- Step Functions
- Secure generative-AI integration
- Prompt-injection risk reduction
- JSON Schema
- Human-in-the-loop automation
- Security testing
- Cost-conscious cloud engineering
- Technical documentation

## Future enhancements

Possible future improvements include:

- Amazon Bedrock inference when account quotas become available
- AWS KMS customer-managed keys
- CI/CD security checks
- Automated secret scanning
- CloudWatch alarms and operational dashboards
- Cost Anomaly Detection integration
- Additional GuardDuty protection plans
- Authentication for a hosted reviewer interface
- Multi-account evidence collection
- Production response adapters protected by additional authorization controls

## Conclusion

The AI CloudSec Incident Responder demonstrates a complete security workflow rather than an isolated AI prompt or cloud-service example.

The project integrates detection, normalization, evidence protection, local AI analysis, schema validation, human authorization, workflow orchestration, safe response simulation, and auditability.

Most importantly, the design treats both security findings and AI output as untrusted, preserves human control, and proves response behavior without risking changes to AWS resources.