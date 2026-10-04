# Security and Cost Review

## Review date

October 4, 2026

## Scope

This review verifies the principal security and cost controls protecting the AI CloudSec Incident Responder Lab in `us-east-1`.

The review covers:

- Amazon S3 evidence storage
- Amazon DynamoDB incident metadata
- AWS Lambda configuration
- Amazon CloudWatch log retention
- Amazon GuardDuty status
- AWS Budgets configuration
- Infrastructure consistency

## Security controls

### Amazon S3 evidence bucket

The evidence bucket passed the configured storage-security checks:

- Server-side encryption: `AES256`
- Versioning: enabled
- Public ACLs: blocked
- Public bucket policies: blocked
- Public bucket access: restricted
- Effective public status: false

The bucket therefore provides encrypted, versioned, and non-public storage for normalized findings, AI investigations, approval records, and dry-run response evidence.

The use of Amazon S3 managed AES-256 encryption is appropriate for the current lab. A customer-managed AWS KMS key remains a possible future enhancement if stronger key-control requirements justify the additional complexity and cost.

### Amazon DynamoDB incidents table

The incident metadata table passed the configured checks:

- Table status: `ACTIVE`
- Billing mode: `PAY_PER_REQUEST`
- Encryption at rest: enabled
- Point-in-time recovery: enabled
- Current item count: 4

On-demand billing avoids provisioned-capacity charges during periods of inactivity. Point-in-time recovery provides protection against accidental modification or deletion of incident metadata.

### AWS Lambda functions

The deployed Lambda functions use a cost-conscious baseline:

| Function | Runtime | Memory | Timeout |
|---|---|---:|---:|
| Finding normalizer | Python 3.13 | 128 MB | 10 seconds |
| Approval request | Python 3.13 | 128 MB | 10 seconds |
| Approval decision | Python 3.13 | 128 MB | 10 seconds |
| Dry-run response | Python 3.13 | 128 MB | 10 seconds |

The low memory allocation and short timeout reduce the potential cost and impact of unexpected or repeated invocations.

### Amazon CloudWatch Logs

All application and workflow log groups use a 14-day retention period:

- Finding normalizer Lambda
- Approval request Lambda
- Approval decision Lambda
- Dry-run response Lambda
- Step Functions approval workflow

Explicit retention prevents indefinite log accumulation while preserving sufficient history for troubleshooting and portfolio demonstrations.

### Amazon GuardDuty

Amazon GuardDuty is enabled in `us-east-1`.

- Detector status: `ENABLED`
- Finding publication frequency: 15 minutes

Optional GuardDuty protection plans remain disabled unless a documented workload requires them. GuardDuty usage should continue to be monitored after any applicable trial period.

## Cost controls

The AWS account has a monthly budget configured as follows:

- Budget name: `Primary budget`
- Monthly limit: USD 15
- Current reported actual cost: USD 0
- Current forecast: unavailable

An unavailable forecast is expected when AWS does not yet have enough usage history. Budget notifications provide visibility into unexpected spending but do not automatically stop AWS resources or charges.

Additional cost protections include:

- DynamoDB on-demand billing
- Small Lambda memory allocations
- Short Lambda execution timeouts
- Fourteen-day log retention
- Restricted GuardDuty feature scope
- Local Ollama inference instead of billable managed-model inference
- Dry-run response actions that make zero resource changes

## Residual considerations

The following controls may be considered in a future production-oriented version:

- Customer-managed AWS KMS keys
- Automated cost-anomaly response
- Additional CloudWatch alarms
- Centralized multi-account logging
- Expanded GuardDuty protection plans
- Automated secret scanning in CI/CD

These enhancements are not required for the current development and portfolio scope.

## Conclusion

The lab currently meets its intended security and cost-control baseline. Evidence storage is encrypted and private, incident metadata is recoverable, compute resources are constrained, logs have finite retention, GuardDuty is operational, and the monthly budget provides cost visibility.

No production containment actions are enabled. All response activity remains subject to explicit human approval and is executed only in `DRY_RUN` mode.