# Environment Setup Notes

## Setup date

September 1, 2026

## AWS services verified

- Amazon Bedrock
- AWS Config
- AWS CloudTrail
- AWS Lambda
- Amazon EventBridge
- Amazon S3
- Amazon DynamoDB
- AWS Systems Manager
- AWS CloudFormation

## Known limitation

Amazon GuardDuty is restricted in the current AWS account.

To preserve the detection-engineering objectives of the project, the lab will use synthetic GuardDuty-compatible findings delivered through Amazon EventBridge.

## Local development environment

- Git 2.55.0
- Visual Studio Code 1.105.1
- GitHub repository configured
- Private GitHub noreply address used for commits