# Sprint 1 Retrospective

## Sprint information

- Sprint: Sprint 1 — AWS Baseline
- Status: Completed
- Completion date: September 7, 2026
- Monthly cost ceiling: USD 15
- AWS resources deployed during this sprint: None

## Summary

Sprint 1 established the Terraform and security baseline required before
deploying AWS resources for the AI CyberSecurity Lab.

The repository now contains a validated Terraform configuration, reusable
naming and tagging conventions, a secure remote-state design, and a
least-privilege deployment-role design.

The sprint intentionally prioritized design, validation, and security controls
before resource deployment.

## Sprint objectives

The objectives were to:

- Configure Terraform and the AWS provider.
- Define reusable project variables.
- Establish consistent naming and tagging.
- Design secure Terraform state management.
- Define the Terraform deployment identity and its security boundaries.
- Validate the complete Terraform baseline.
- Avoid premature deployment and unnecessary AWS costs.

All planned objectives were completed.

## Completed work

### Terraform provider configuration

The Terraform root module now includes:

- Terraform version constraints.
- AWS provider version constraints.
- A configurable AWS region.
- AWS provider configuration.
- A committed provider dependency lock file.

The provider uses the configured project region and contains no embedded AWS
credentials.

### Variables and validation

Terraform variables define:

- Project name
- Environment
- AWS region
- Resource owner

Environment values are validated against the approved environments:

- `dev`
- `test`
- `prod`

The initial deployment environment will be `dev`.

### Naming and tagging conventions

Reusable local values provide:

- A consistent project-and-environment resource prefix.
- Common tags for all supported AWS resources.
- Project ownership information.
- Environment identification.
- Terraform management attribution.

The AWS provider applies the common tags through `default_tags`.

### Terraform state design

The remote-state strategy is documented in
`docs/terraform-state.md`.

Before the first AWS resource deployment, the main Terraform configuration will
be migrated from local state to a protected Amazon S3 backend.

The design includes:

- A dedicated S3 state bucket.
- S3 Block Public Access.
- Server-side encryption.
- S3 versioning.
- TLS enforcement.
- Native S3 state locking.
- Least-privilege backend permissions.
- Recovery and migration procedures.

DynamoDB state locking was not selected because native S3 locking is available
in the current Terraform version and the older DynamoDB mechanism is
deprecated.

### Deployment role design

The least-privilege deployment model is documented in
`docs/terraform-deployment-role.md`.

The design establishes:

- Temporary credentials for Terraform deployments.
- MFA for human access.
- Separate identities for humans, automation, and workloads.
- Project- and environment-scoped permissions.
- A permissions boundary for roles created by Terraform.
- Restricted `iam:PassRole` access.
- Protection against IAM users and permanent access-key creation.
- Human review of destructive Terraform plans.
- CloudTrail and IAM Access Analyzer review requirements.

The existing IAM user and passkey remain part of the initial account-access
controls. Permanent access keys will not be created merely for Terraform
convenience.

## Validation evidence

The final Terraform checks were executed from
`infrastructure/terraform`.

### Formatting

Command:

```powershell
terraform fmt -check
```

Result:

```text
No output. All Terraform files passed the formatting check.
```

### Configuration validation

Command:

```powershell
terraform validate
```

Result:

```text
Success! The configuration is valid.
```

### Provider verification

Command:

```powershell
terraform providers
```

Result:

```text
Providers required by configuration:
.
└── provider[registry.terraform.io/hashicorp/aws] ~> 6.0
```

### Git protection

The repository excludes:

- `.terraform` working directories.
- Terraform state files.
- Terraform state backup files.
- `.tfvars` files.
- `.tfvars.json` files.
- Local Python virtual environments.
- Local editor settings.

The final pre-retrospective Git check reported a clean working tree synchronized
with `origin/main`.

## Security decisions

The sprint produced the following security decisions:

1. Terraform will not use the AWS root user.
2. AWS credentials will not be committed to Git.
3. Human and automated deployment identities will remain separate.
4. Terraform will use temporary credentials.
5. Human authentication will require MFA.
6. Terraform state will be treated as security-sensitive data.
7. Remote state must be protected before the first deployment.
8. IAM permissions will be introduced incrementally.
9. Workload roles will remain separate from the deployment role.
10. Destructive changes require human plan review.
11. Resource naming and tags must identify the project and environment.
12. Infrastructure decisions must respect the USD 15 monthly cost ceiling.

## Challenges and resolutions

### Terraform file placement

Terraform files were initially placed in different directories, which caused
VS Code to report an unresolved variable reference.

The files were moved into the same Terraform root module:

```text
infrastructure/terraform/
```

After the correction, the editor warning disappeared and Terraform validation
succeeded.

### Local editor configuration

VS Code created a local workspace settings directory. The project `.gitignore`
was updated so machine-specific editor configuration would not be committed.

### GuardDuty restriction

Amazon GuardDuty remains unavailable because of an AWS account restriction.

The project will preserve its detection-engineering objectives by using
synthetic GuardDuty-compatible findings submitted through EventBridge.

### Remote-state sequencing

The state backend cannot manage the resources required to create itself.

The project therefore selected a separate bootstrap process for the future S3
backend. No backend resources were deployed during this sprint.

## Lessons learned

- No output from `terraform fmt -check` indicates success.
- `terraform validate` verifies configuration structure, but it does not prove
  that AWS credentials or deployment permissions are correct.
- Terraform state can contain security-sensitive information.
- Backend infrastructure requires a separate bootstrap decision.
- A permissions boundary limits maximum permissions but does not grant
  permissions by itself.
- `iam:PassRole` requires careful resource and service restrictions.
- Trust policies and permissions policies answer different security questions.
- Documentation before deployment reduces rework and makes security decisions
  auditable.
- Small, consistent sessions can produce meaningful engineering progress.

## Items intentionally deferred

The following items are designed but not yet implemented:

- Remote S3 state bucket.
- Native S3 state locking test.
- Terraform state migration.
- Permissions boundary.
- Terraform deployment permissions policy.
- Human deployment role.
- Temporary-credential AWS CLI profile.
- GitHub Actions deployment identity.
- AWS resource deployment.

These items will be implemented incrementally when the corresponding project
stage requires them.

## Sprint 2 readiness

The project is ready to begin Sprint 2 because:

- The repository is clean and synchronized.
- Terraform formatting passes.
- Terraform validation passes.
- Provider constraints are locked.
- Naming and tagging conventions exist.
- State protections are documented.
- Deployment access controls are documented.
- The architecture and threat model identify the required trust boundaries.
- GuardDuty findings can be simulated without depending on the restricted
  service.

## Sprint 2 preview

Sprint 2 — Detection Pipeline will begin with:

1. Creating a protected evidence S3 bucket.
2. Creating an EventBridge custom event bus.
3. Defining the normalized finding schema.
4. Creating synthetic GuardDuty-compatible test events.
5. Connecting the initial event-processing components.

Every deployment will continue to follow the project security and cost
guardrails.

## Definition of done

- [x] Terraform provider configured
- [x] Terraform version constraints defined
- [x] Provider lock file committed
- [x] Project variables defined
- [x] Environment validation implemented
- [x] Naming conventions implemented
- [x] Common tags implemented
- [x] Remote-state approach documented
- [x] Deployment role design documented
- [x] Terraform formatting verified
- [x] Terraform configuration validated
- [x] Provider requirement verified
- [x] Sensitive Terraform files excluded from Git
- [x] Sprint decisions and deferred work documented

Sprint 1 — AWS Baseline is complete.