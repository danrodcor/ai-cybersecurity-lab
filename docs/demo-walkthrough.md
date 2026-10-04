# End-to-End Demo Walkthrough

## Purpose

This walkthrough demonstrates the complete AI CloudSec Incident Responder workflow, from security-finding ingestion through human approval and a safe dry-run response.

The workflow supports three terminal outcomes:

- `APPROVED` — produces a simulated response with zero resource changes.
- `REJECTED` — closes the workflow without invoking the response Lambda.
- `EXPIRED` — records the expired approval without invoking the response Lambda.

## Prerequisites

Before starting the demonstration, confirm:

- The Python virtual environment is active.
- AWS credentials are available.
- Terraform infrastructure is deployed in `us-east-1`.
- Ollama is running locally.
- The `qwen3:14b` model is available.
- Required environment variables are configured.
- The repository is clean and synchronized.

Verify the environment:

```powershell
aws sts get-caller-identity
ollama ps
terraform -chdir=infrastructure\terraform plan
git status
```

Expected results:

- AWS returns the active account identity.
- Ollama reports the local model.
- Terraform reports no infrastructure changes.
- Git reports a clean working tree.

## 1. Validate the project

Run the complete validation suite:

```powershell
.\scripts\validate_project.ps1
```

Expected result:

```text
PROJECT VALIDATION: PASS
```

This confirms the JSON contracts, unit tests, Terraform formatting, Terraform configuration, and Git whitespace checks.

## 2. Publish a synthetic security finding

Publish the safe GuardDuty-compatible sample through the custom EventBridge bus:

```powershell
.\scripts\publish_sample_event.ps1
```

Expected result:

- EventBridge reports zero failed entries.
- The finding-normalizer Lambda receives the event.
- A normalized evidence object is written to Amazon S3.
- A new incident record is written to DynamoDB with status `NEW`.
- The incident is marked as synthetic.

The same normalizer also accepts native GuardDuty findings routed through the default EventBridge bus.

## 3. Retrieve the normalized finding

Identify the new finding through the Lambda logs or DynamoDB incident table.

The normalized evidence object uses this key structure:

```text
normalized-findings/<finding-id>.json
```

Download the selected finding to a temporary local file:

```powershell
aws s3 cp `
    "s3://$env:EVIDENCE_BUCKET_NAME/normalized-findings/<finding-id>.json" `
    "$env:TEMP\demo-normalized-finding.json"
```

Replace `<finding-id>` with the generated normalized finding identifier.

## 4. Run the local AI investigation

Invoke the local investigation workflow and persist the validated result:

```powershell
python scripts\run_local_investigation.py `
    "$env:TEMP\demo-normalized-finding.json" `
    --model-id qwen3:14b `
    --persist
```

The runner:

1. Applies the evidence allow-list.
2. Removes excluded sensitive identifiers.
3. Sends the restricted evidence package to local Ollama.
4. Requests structured JSON from Qwen3 14B.
5. Validates the model response.
6. Requires `requires_human_approval` to be `true`.
7. Writes the validated investigation to Amazon S3.
8. Updates the DynamoDB incident record.

Expected evidence key:

```text
ai-investigations/<finding-id>.json
```

Expected provider metadata:

```text
provider: ollama
model_id: qwen3:14b
```

## 5. Open the reviewer interface

Start the local Streamlit interface:

```powershell
streamlit run app\reviewer.py
```

The reviewer interface retrieves pending approvals from AWS and presents:

- Finding identifier
- Investigation summary
- Confidence level
- Proposed response actions
- Model provider and model identifier
- Approval expiration
- `DRY_RUN` response mode

AWS credentials remain outside the local model process.

## 6. Start and review an approval

Start the Step Functions approval workflow using the validated investigation result.

The workflow:

1. Invokes the approval-request Lambda.
2. Persists a `PENDING` approval request.
3. Waits for a human decision.
4. Routes the result according to the decision or expiration time.

Use the Streamlit interface to submit either `APPROVED` or `REJECTED`.

Each decision records:

- Approval identifier
- Finding identifier
- Reviewer identity
- Decision timestamp
- Optional reviewer comment
- Response mode

## 7. Validate the approved branch

For an approved request, verify:

- Step Functions completes with workflow status `APPROVED`.
- DynamoDB records approval status `APPROVED`.
- The dry-run response Lambda is invoked.
- Amazon S3 contains a dry-run response object.
- The response status is `SIMULATED`.
- `executed` is `false`.
- `resource_changes` is `0`.

Expected evidence key:

```text
dry-run-responses/<finding-id>/<approval-id>.json
```

No AWS workload is isolated, modified, deleted, or otherwise contained.

## 8. Validate the rejected branch

For a rejected request, verify:

- Step Functions completes with workflow status `REJECTED`.
- DynamoDB records approval status `REJECTED`.
- The dry-run response Lambda is not invoked.
- No dry-run response object exists for the approval.

The rejected branch closes safely without performing a response action.

## 9. Validate the expired branch

For an expired request, verify:

- Step Functions completes with workflow status `EXPIRED`.
- DynamoDB records approval status `EXPIRED`.
- The status update applies only when the stored approval is still `PENDING` and the approval identifier matches.
- The dry-run response Lambda is not invoked.
- No dry-run response object exists for the approval.

This conditional update prevents an expiration path from overwriting a completed human decision.

## 10. Review audit evidence

The demonstration produces an auditable evidence chain across:

- EventBridge event delivery
- Lambda execution logs
- Normalized S3 evidence
- DynamoDB incident metadata
- Validated AI investigation output
- Approval request records
- Approval decision records
- Step Functions execution history
- Dry-run response records

CloudWatch log groups retain application and workflow logs for 14 days.

## Security properties demonstrated

The completed demonstration confirms:

- Findings are treated as untrusted input.
- Evidence is normalized before AI processing.
- Only allow-listed evidence reaches the model.
- Local model access is restricted to the trusted workstation.
- AI output is treated as untrusted.
- Structured output must pass schema and safety validation.
- Every proposed response requires human approval.
- Rejected and expired approvals cannot invoke the response.
- Approved responses operate only in `DRY_RUN` mode.
- Dry-run responses make zero resource changes.
- Evidence is encrypted and non-public.
- Workflow activity is auditable.

## Supporting evidence

Additional implementation evidence is available in:

- [Architecture](architecture.md)
- [Approval workflow validation](approval-workflow-validation.md)
- [Security and cost review](security-cost-review.md)