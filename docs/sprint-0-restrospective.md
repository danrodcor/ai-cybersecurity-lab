# Sprint 0 Retrospective

## Sprint objective

Establish a secure and documented foundation for the AI-assisted
incident-response laboratory before deploying AWS resources.

## Completed work

- Verified the availability of the required AWS services.
- Documented the GuardDuty account restriction.
- Configured Git, GitHub, VS Code, Python, and the local virtual environment.
- Created and published the project repository.
- Initialized and validated the Terraform workspace.
- Defined the project charter and USD 15 monthly cost ceiling.
- Documented the system architecture, data flows, and trust boundaries.
- Created an initial STRIDE threat model with seven threats and mitigations.

## What went well

- Small, focused sessions kept the project moving consistently.
- Git commits provide a clear history of each project decision.
- Security and cost controls were documented before resource deployment.
- The architecture and threat model explicitly preserve human approval.
- Terraform initialized successfully with a locked AWS provider version.

## Challenges

- Amazon GuardDuty is unavailable because of an AWS account restriction.
- Git and GitHub required initial local setup and authentication.
- The threat-model file was initially staged before its contents were saved.

## Decisions made

- Use synthetic GuardDuty-compatible findings through EventBridge.
- Treat all evidence and AI-generated output as untrusted data.
- Allow only approved evidence fields to reach Amazon Bedrock.
- Require validation and human approval before any proposed response.
- Keep response actions in dry-run mode during the laboratory.
- Maintain a USD 15 monthly operating-cost ceiling.

## Lessons learned

- Review staged changes before committing them.
- Repository documentation is part of the security design.
- Trust boundaries help identify where validation is required.
- AI output must never be treated as an authorization decision.
- Environmental restrictions can be handled without abandoning the
  engineering objective.

## Sprint 1 readiness

Sprint 0 has established the documentation and local tooling needed to begin
the AWS baseline.

The next sprint will focus on:

- Terraform AWS provider configuration
- Naming and tagging conventions
- Terraform state design
- Least-privilege deployment-role design
- Formatting and validation checks