# Approval Workflow Validation

## Scope

This validation confirms that the human-approval workflow handles approved,
rejected, and expired requests without executing real response actions.

- AWS Region: `us-east-1`
- Workflow type: AWS Step Functions Standard
- Response mode: `DRY_RUN`
- Model provider used for test investigations: local Ollama
- Test data: synthetic GuardDuty-compatible findings

## Results

| Path | Expected outcome | Result |
|---|---|---|
| `APPROVED` | Invoke the dry-run response Lambda and persist a simulated response | PASS |
| `REJECTED` | Complete without invoking the dry-run response Lambda | PASS |
| `EXPIRED` | Persist `EXPIRED` and complete without invoking the dry-run response Lambda | PASS |

## Approved path

- Finding ID: `f7807877-a08a-53b4-8e2b-a2ba89e9dd96`
- Approval ID: `0e51ed68-090b-4ded-8c24-dafa946c22af`
- Response ID: `b91c97d7-eb8f-5846-9cc0-065255f741b9`
- Final workflow status: `APPROVED`
- Response status: `SIMULATED`
- Actual execution: `false`
- Resource changes: `0`

## Rejected path

- Finding ID: `14794202-e0de-5f95-94d6-0ec63d2687cc`
- Approval ID: `4b490e4c-d231-4c2b-a9a6-f71748ec5bdd`
- Final workflow status: `REJECTED`
- Stored approval status: `REJECTED`
- Dry-run response objects: `0`

## Expired path

- Finding ID: `973f4512-9a49-5450-a7fb-3d5aa5a50d1d`
- Approval ID: `9e9ef2fe-01ea-4402-992a-225138b36c5b`
- Final workflow status: `EXPIRED`
- Stored approval status: `EXPIRED`
- Dry-run response objects: `0`

The initial expiration test exposed a traceability gap: Step Functions returned
`EXPIRED`, but DynamoDB retained `PENDING`. The workflow was corrected to use a
conditional DynamoDB update that persists `EXPIRED` only when the request is
still `PENDING` and the approval identifier matches. The corrected workflow was
deployed and successfully retested.

## Validated controls

- AI recommendations cannot proceed without a validated human decision.
- Rejected and expired requests cannot invoke the response Lambda.
- Approved actions remain simulation-only and perform no resource changes.
- Expiration persistence uses a conditional update to protect completed
  decisions from replacement.
- Step Functions has only the additional DynamoDB permission required to update
  the expiration status.
