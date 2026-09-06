# Terraform State Design

## Purpose

This document defines how Terraform state will be protected for the
AI CyberSecurity Lab.

Terraform state maps the resources declared in the configuration to the
resources deployed in AWS. Because state can contain resource identifiers,
configuration details, and sensitive values, it must be protected as
security-sensitive data.

## Current decision

The project will use local state only while the configuration contains no
deployed AWS resources.

Before the first deployment, the main Terraform configuration will be migrated
to a remote Amazon S3 backend.

The remote backend will use:

- A dedicated S3 bucket
- S3 versioning
- S3 Block Public Access
- Server-side encryption
- TLS for data in transit
- Native S3 state locking
- Least-privilege IAM permissions
- Audit logging for state access

The project will not use DynamoDB for state locking because that mechanism is
deprecated in current Terraform versions.

## Planned backend configuration

The future backend will follow this structure:

```hcl
terraform {
  backend "s3" {
    bucket       = "REPLACE_WITH_STATE_BUCKET"
    key          = "ai-cybersecurity-lab/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

The bucket name will be supplied only after the backend infrastructure exists.

Backend configuration cannot reference Terraform variables or local values, so
the backend region and object key must be supplied directly or through a
separate backend configuration file.

## Security controls

### S3 bucket

The state bucket must:

- Reject all public access.
- Enable versioning to support recovery from accidental changes.
- Encrypt every object at rest.
- Reject requests that do not use TLS.
- Restrict access to the Terraform deployment identity.
- Prevent accidental deletion of state versions.
- Use a dedicated prefix for each environment.

### State locking

Terraform will use the native S3 lock file:

```hcl
use_lockfile = true
```

The lock prevents concurrent Terraform operations from modifying the same state
at the same time.

The deployment identity requires permission to read, create, and delete the
`.tflock` object. Delete permission is required for the lock file but should not
be granted unnecessarily to the state object itself.

### IAM access

The Terraform deployment identity should receive only the permissions needed
to:

- List the specific backend bucket and prefix.
- Read and update the state object.
- Read, create, and delete the lock file.
- Use the selected encryption key when applicable.

Human access to the state bucket should be limited to emergency recovery and
audited.

### Sensitive data

Sensitive values should not be placed directly in Terraform configuration,
variable files, command history, or Git.

Marking a Terraform value as `sensitive` only hides it from normal CLI output;
it does not necessarily prevent it from being stored in state.

## Bootstrap approach

The backend cannot store its own state before the bucket exists. Therefore, the
backend infrastructure will be created separately from the main configuration.

The planned process is:

1. Create a small backend bootstrap configuration.
2. Create the protected S3 bucket and its security controls.
3. Record and review the resulting bucket name.
4. Add the S3 backend configuration to the main Terraform root module.
5. Run `terraform init -migrate-state`.
6. Confirm that the remote state and lock file work.
7. Remove any obsolete local state files securely.

No backend resources will be deployed during the current design session.

## Failure and recovery

- If a Terraform operation fails, verify that the lock belongs to no active
  process before attempting to remove it.
- Never delete a lock merely to bypass an unknown concurrent operation.
- Use S3 version history to recover an earlier state only after reviewing the
  affected infrastructure.
- Back up the current state before any backend migration or manual recovery.
- Never commit state or backup-state files to Git.

## Cost considerations

Terraform state files are small, so S3 storage and request costs should remain
minimal.

Any optional customer-managed KMS key or additional audit logging must be
evaluated against the project's USD 15 monthly cost ceiling before deployment.

## Implementation status

- [x] Remote-state approach documented
- [ ] Backend bootstrap configuration created
- [ ] S3 state bucket deployed
- [ ] State locking tested
- [ ] Main state migrated
- [ ] Recovery procedure tested

## References

- https://developer.hashicorp.com/terraform/language/backend/s3
- https://developer.hashicorp.com/terraform/language/state/backends
- https://developer.hashicorp.com/terraform/language/manage-sensitive-data