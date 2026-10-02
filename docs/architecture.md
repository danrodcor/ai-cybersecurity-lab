# Architecture

## Status

Planned architecture — not yet deployed.

## Overview

The AI CloudSec Incident Responder uses an event-driven AWS architecture to process native GuardDuty findings and synthetic security fixtures, preserve evidence, generate an AI-assisted investigation, and require human approval before any simulated response.

## Architecture diagram

```mermaid
flowchart TD
    subgraph Input["Untrusted input boundary"]
        A["Synthetic GuardDuty-compatible finding"]
        B["Amazon EventBridge custom bus"]
        U["Amazon GuardDuty<br/>Native and sample findings"]
        V["Amazon EventBridge default bus"]

        A --> B
        U --> V
    end

    subgraph Processing["AWS detection and evidence boundary"]
        C["Finding-normalizer Lambda"]
        D[("DynamoDB<br/>Incident metadata")]
        E[("Amazon S3<br/>Evidence archive")]

        C --> D
        C --> E
    end

    subgraph Local["Local investigation boundary"]
        F["Investigation runner"]
        G["Evidence collector"]
        H["Allow-listed evidence package"]

        F --> G
        G --> H
    end

    subgraph AI["Local AI trust boundary"]
        I["Ollama<br/>Qwen3 14B"]
        J["Schema and safety validation"]
        K{"Valid structured output?"}
        T["Reject unsafe or invalid output"]

        I --> J
        J --> K
        K -- "No" --> T
    end

    subgraph Approval["Human-approval boundary"]
        L["AWS Step Functions"]
        M["Human-review interface<br/>(planned)]
        N{"Decision"}
        O["Dry-run response Lambda<br/>(planned)]
        P["Close without action"]

        L --> M
        M --> N
        N -- "Approve" --> O
        N -- "Reject" --> P
    end

    B --> C
    V --> C
    D --> F
    E --> F
    H --> I
    K -- "Yes" --> D
    K -- "Yes" --> E
    K -- "Yes" --> L

    C -. "Logs and metrics" .-> Q["Amazon CloudWatch"]
    L -. "Workflow history" .-> Q
    R["AWS control-plane activity"] -.-> S["AWS CloudTrail"]
```

## Data flow

| Step | Source | Destination | Data |
|---:|---|---|---|
| 1 | Synthetic fixture | EventBridge custom bus | GuardDuty-compatible JSON with no sensitive data |
| 2 | Amazon GuardDuty | EventBridge default bus | Native or AWS-generated sample finding |
| 3 | EventBridge rules | Normalizer Lambda | Original event envelope |
| 4 | Normalizer Lambda | DynamoDB | Incident ID, severity, status, timestamps, and normalized metadata |
| 5 | Normalizer Lambda | S3 | Normalized evidence document |
| 6 | DynamoDB and S3 | Local investigation runner | Existing normalized finding selected for investigation |
| 7 | Local investigation runner | Evidence collector | Normalized finding processed on the trusted workstation |
| 8 | Evidence collector | Local Ollama model | Size-limited and allow-listed evidence package |
| 9 | Local Ollama model | Schema and safety validator | Untrusted structured investigation candidate |
| 10 | Schema and safety validator | S3 and DynamoDB | Validated investigation, provider metadata, and completion status |
| 11 | Local runner or operator | Step Functions | Approval-ready investigation, evidence reference, and unique approval ID |
| 12 | Step Functions | Human reviewer | Evidence summary and proposed response |
| 13 | Human reviewer | Dry-run response | Explicit approval or rejection |
| 14 | Dry-run response | Audit trail | Simulated action result; no real containment |

## Trust boundaries

### Untrusted input boundary

Native GuardDuty findings and synthetic fixtures are treated as untrusted. AWS-generated sample findings are explicitly identified as synthetic before persistence. Schema validation and normalization must occur before their fields are used by downstream components.

### Evidence boundary

S3 and DynamoDB hold the authoritative incident evidence. Access is restricted through service-specific IAM roles, encryption, and public-access controls.

### Local investigation boundary

The local runner retrieves an existing normalized finding from AWS, applies the evidence allow-list, invokes the configured model, validates the result, and persists only an approved structured document. AWS credentials remain outside the model process.

### AI boundary

Qwen3 14B currently runs through Ollama on the trusted workstation. The Ollama client accepts only loopback HTTP endpoints, and the model receives only size-limited, allow-listed evidence. Model output is untrusted and must satisfy the versioned JSON schema and safety checks before persistence. Amazon Bedrock remains an optional provider adapter for future use when account quotas become available.

### Human-approval boundary

AWS Step Functions now creates and monitors pending approval requests through dedicated Lambda functions and DynamoDB state. Human decisions are structurally validated, preserved in Amazon S3, and restricted to `DRY_RUN`. The reviewer interface and simulated response function remain planned.

### Audit boundary

CloudWatch captures application logs and metrics. CloudTrail records relevant AWS control-plane activity.

## Security decisions

- Accept native GuardDuty findings and synthetic fixtures through separate EventBridge routes that converge on the same normalizer.
- Enable GuardDuty foundational detection in `us-east-1`; keep optional protection plans disabled unless a documented workload requires them.
- Classify AWS-generated GuardDuty samples as synthetic evidence before persistence.
- Do not place credentials, account identifiers, or sensitive data in event fixtures.
- Preserve normalized evidence in Amazon S3 separately from searchable incident metadata in DynamoDB.
- Send only required and size-limited evidence to the configured model provider; local Ollama access is restricted to loopback HTTP.
- Validate AI output before storing or presenting it as a recommendation.
- Keep evidence collection, AI processing, and response roles separate.
- Require human approval before every simulated response.
- Implement response actions only in dry-run mode.
- Encrypt stored evidence and block public access.
- Review every Terraform plan before deployment.

## Failure behavior

- Invalid input is rejected and logged without invoking the configured model.
- Missing or oversized evidence stops the investigation before model invocation.
- An unavailable local model leaves the existing AWS incident unchanged and available for retry.
- Invalid or unsafe model output is rejected and cannot be persisted or forwarded for approval.
- Persistence requires an existing DynamoDB incident and explicit human-approval metadata.
- Workflow failures retain the original incident and evidence for manual review.

## Deployment approach

Infrastructure will be introduced incrementally through Terraform. Each change must pass formatting, validation, plan review, security review, and cost review before deployment.