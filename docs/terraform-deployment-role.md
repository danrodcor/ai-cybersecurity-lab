# Terraform Deployment Role Design

## Purpose

This document defines the access model for deploying the AI CyberSecurity Lab
with Terraform.

The deployment identity must have enough permission to manage approved
laboratory resources without receiving unrestricted administrator access.

## Security decision

Terraform deployments will use temporary AWS credentials.

The project will not:

- Use the AWS account root user for deployments.
- Store AWS access keys in Git, Terraform files, or variable files.
- Give Terraform unrestricted administrator access.
- Reuse Terraform deployment permissions as Lambda runtime permissions.
- Allow an automated workflow to share a human deployment identity.

The existing IAM user and passkey protect initial console access. Before local
Terraform deployment, the preferred approach is to configure federated or
IAM Identity Center access that provides temporary credentials.

If temporary federated access is unavailable in the laboratory account, a
restricted STS role-assumption workflow may be evaluated separately. Permanent
access keys must not be created merely for convenience.

## Identity separation

| Identity | Purpose | Trust source |
| --- | --- | --- |
| Human operator | Run reviewed Terraform plans locally | Federated human identity with MFA |
| Terraform deployment role | Create and manage approved lab resources | Human operator role |
| GitHub Actions role | Future automated validation or deployment | GitHub OpenID Connect |
| Lambda execution role | Allow a Lambda function to access required services | AWS Lambda service |
| Step Functions role | Future human-approval workflow | AWS Step Functions service |

Human, automation, and workload identities must remain separate.

A future GitHub Actions role must be restricted to:

- The `danrodcor/ai-cybersecurity-lab` repository.
- An approved branch or GitHub environment.
- Short-lived OpenID Connect credentials.
- The minimum permissions required by the workflow.

Adding GitHub Actions as a trusted principal must not broaden the trust policy
of the human deployment role.

## Trust assumptions

The initial design assumes:

- Deployment occurs in one dedicated AWS account.
- The first environment is `dev`.
- The primary AWS region is `us-east-1`.
- One authorized human operator reviews Terraform plans.
- MFA is required for human access.
- Production workloads and customer information are not present.
- All resources use the project naming prefix and common tags.
- Destructive operations require explicit human review.

## Human deployment workflow

The expected workflow is:

1. Authenticate through the approved human identity using MFA.
2. Obtain temporary AWS credentials.
3. Assume the Terraform deployment role.
4. Run `terraform plan`.
5. Review resource changes, IAM changes, replacements, and deletions.
6. Run `terraform apply` only after the plan is understood.
7. Allow the temporary session to expire after the work is complete.

The session should use a descriptive name when supported so that activity can
be identified in AWS CloudTrail.

## Permission model

Effective permissions are limited by the intersection of:

- The deployment role permissions policy.
- The permissions boundary, when attached.
- Any session policy.
- Any applicable AWS Organizations policies.
- Resource-based policies.

An explicit deny in an applicable policy overrides an allow.

## Required service access

The exact actions will be refined as Terraform resources are implemented. The
initial deployment role may require scoped access to the following services.

| Service | Intended purpose | Scope requirement |
| --- | --- | --- |
| Amazon S3 | Terraform state and protected evidence storage | Approved buckets and prefixes only |
| Amazon EventBridge | Custom event bus and routing rules | Project-prefixed resources only |
| AWS Lambda | Finding normalization and investigation functions | Project-prefixed functions only |
| Amazon DynamoDB | Incident metadata storage | Project-prefixed tables only |
| Amazon CloudWatch Logs | Lambda and workflow logging | Project log groups only |
| AWS IAM | Create workload roles and policies | Project-prefixed identities with a required boundary |
| AWS Systems Manager | Approved configuration values if needed | Project parameter paths only |
| Amazon Bedrock | Future AI-assisted investigation | Approved models and regions only |
| AWS Step Functions | Future human-approval workflow | Project-prefixed state machines only |

Permission for a service will not be granted until a corresponding Terraform
resource requires it.

## IAM guardrails

Terraform may need limited IAM permissions to create workload roles. These
permissions must be constrained by the following controls:

- IAM role and policy names must use the project prefix.
- Any role created by Terraform must receive the approved permissions boundary.
- `iam:PassRole` must apply only to project workload roles.
- Passed roles must be limited to approved AWS services.
- Terraform must not create IAM users.
- Terraform must not create access keys.
- Terraform must not modify the account password policy.
- Terraform must not manage the root user.
- Terraform must not detach or replace its own permissions boundary.
- Terraform must not create unrestricted administrator policies.
- Workload roles must receive separate, service-specific policies.

A permissions boundary defines the maximum permissions available to an
identity. It does not grant permissions by itself.

## Resource restrictions

Where supported, permissions should be restricted using:

- Explicit resource ARNs.
- The `ai-cybersecurity-lab` resource prefix.
- The `Environment = dev` tag.
- The project common tags.
- The `us-east-1` region.
- Request-tag and resource-tag policy conditions.
- Approved AWS service principals.

Not every AWS action supports resource-level or tag-based restrictions.
Unsupported actions must be identified and reviewed before permission is
granted.

## Terraform state access

The deployment role requires access to the remote-state backend described in
`docs/terraform-state.md`.

State permissions should allow:

- Listing the specific state bucket and project prefix.
- Reading the project state object.
- Updating the project state object.
- Reading, creating, and deleting the corresponding lock file.

The role should not receive unnecessary access to unrelated bucket objects.

Delete permission required for the lock file must not automatically grant
delete permission for the Terraform state object.

## Explicit exclusions

The deployment role does not require permission to:

- Change account contact or billing information.
- Leave or modify an AWS Organization.
- Create IAM users or long-term credentials.
- Disable account security controls.
- Modify unrelated CloudTrail trails.
- Modify unrelated AWS Config resources.
- Access resources belonging to another project.
- Deploy resources outside approved regions.
- Create public S3 buckets.
- Disable encryption or versioning on protected storage.

These exclusions should be enforced through absence of permission and, where
appropriate, explicit deny guardrails.

## Destructive operations

Terraform plans containing deletion or replacement require human review.

Particular attention is required for:

- S3 buckets and stored evidence.
- Terraform state resources.
- DynamoDB tables.
- IAM roles and policies.
- CloudWatch log groups.
- Encryption keys.
- Resources containing audit evidence.

Deletion protection, retention policies, or lifecycle controls should be used
where supported and economically reasonable.

## Auditing and review

Deployment activity must be attributable and reviewable.

The design requires:

- AWS CloudTrail recording role activity.
- Descriptive role-session names or source identity when supported.
- Terraform plans reviewed before application.
- Commit history documenting infrastructure changes.
- IAM Access Analyzer validation for new policies.
- Periodic removal of unused actions and resources.
- Review of denied actions before expanding permissions.

An access-denied error should not automatically result in broader permissions.
The missing action, resource, and condition must first be identified.

## Implementation approach

The role will be implemented incrementally:

1. Document the trust model and permission boundaries.
2. Define the permissions boundary in Terraform.
3. Define the deployment permissions policy.
4. Create the deployment role through an approved bootstrap process.
5. Configure a temporary-credential AWS CLI profile.
6. Run policy validation and `terraform plan`.
7. Deploy one controlled development resource.
8. Review CloudTrail and Access Analyzer evidence.
9. Remove permissions that are not required.
10. Document any approved permission expansion.

No IAM role or policy will be deployed during the current design session.

## Validation criteria

The design is complete when:

- The trusted human or automation identity is explicitly identified.
- Human access requires temporary credentials and MFA.
- Resource permissions are scoped to the project and environment.
- IAM role creation requires a permissions boundary.
- `iam:PassRole` is restricted to approved workload roles.
- Terraform cannot create IAM users or access keys.
- State-bucket permissions match the remote-state design.
- Human and automated deployment roles remain separate.
- Policy validation reports no security errors.
- The repository contains no AWS credentials.

## Implementation status

- [x] Trust assumptions documented
- [x] Required service categories documented
- [x] IAM guardrails documented
- [x] Destructive-operation controls documented
- [ ] Permissions boundary implemented
- [ ] Deployment permissions policy implemented
- [ ] Human deployment role created
- [ ] Temporary-credential profile configured
- [ ] Policy validated with IAM Access Analyzer
- [ ] Controlled deployment tested

## References

- https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_monitor.html