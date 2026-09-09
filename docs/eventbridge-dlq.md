# EventBridge Dead-Letter Queue Design

## Purpose

The detection pipeline will use an Amazon SQS dead-letter queue (DLQ) to preserve security events that Amazon EventBridge cannot deliver successfully to the normalization Lambda function.

The DLQ protects the delivery stage of the pipeline:

1. A synthetic GuardDuty-format finding enters the custom EventBridge bus.
2. An EventBridge rule matches the finding.
3. EventBridge attempts to invoke the normalization Lambda function.
4. EventBridge retries temporary delivery failures.
5. After the retry policy is exhausted, EventBridge sends the undelivered event to the DLQ.
6. An operator investigates the failure and replays the event after correcting the cause.

## Scope

This design covers a target DLQ attached to an EventBridge rule target.

It does not capture events that a producer fails to submit successfully to EventBridge. Producers must inspect the `FailedEntryCount` and individual entries returned by the `PutEvents` operation and handle failed submissions separately.

The queue will not be attached directly to the custom event bus. It will be referenced by the future EventBridge target that invokes the normalization Lambda function.

## Planned AWS resources

The implementation will add:

- One standard Amazon SQS queue.
- One SQS resource policy.
- One EventBridge target dead-letter configuration.
- One EventBridge target retry policy.
- One CloudWatch alarm for visible DLQ messages.

The resources will be deployed in `us-east-1`, the same region as the EventBridge rule and the rest of the development pipeline.

## Queue design

| Setting | Planned value | Reason |
| --- | --- | --- |
| Queue type | Standard | EventBridge target DLQs do not support FIFO queues. |
| Name | `ai-cybersecurity-lab-dev-eventbridge-dlq` | Follows the project naming convention. |
| Message retention | 14 days | Provides investigation time while limiting unnecessary retention. |
| Encryption | SQS-managed encryption | Protects messages at rest without introducing a customer-managed KMS key or additional cost. |
| Public exposure | None | The queue will not use a policy that grants anonymous or broad account access. |
| Region | `us-east-1` | The DLQ must be in the same region as the EventBridge rule. |
| Terraform deletion protection | `prevent_destroy` | Requires an intentional configuration change before Terraform can destroy the queue. |

## Least-privilege access

The queue resource policy will allow the EventBridge service principal to perform only:

```text
sqs:SendMessage
```

The permission will include an `aws:SourceArn` condition that restricts access to the specific EventBridge rule that invokes the normalization Lambda function.

Planned authorization:

```text
Principal: events.amazonaws.com
Action: sqs:SendMessage
Resource: EventBridge DLQ ARN
Condition: aws:SourceArn equals the detection rule ARN
```

The queue policy will also deny requests made without secure transport.

The future Terraform deployment policy will grant only the SQS permissions required to create and manage the queue and its policy. Runtime components will not receive permission to delete DLQ messages unless their recovery responsibilities require it.

Administrative identities in the AWS account may retain broader access according to the account's existing IAM configuration.

## Retry strategy

The initial EventBridge target configuration will use:

| Setting | Planned value |
| --- | --- |
| Maximum event age | 3,600 seconds |
| Maximum retry attempts | 6 |

These values allow retries for temporary delivery failures while making persistent problems visible promptly during development.

The values may be revised after observing Lambda invocation behavior, throttling, delivery latency, and failure rates.

## Monitoring

A CloudWatch alarm will monitor the SQS metric:

```text
ApproximateNumberOfMessagesVisible
```

The alarm will enter the alarm state when one or more messages are visible in the DLQ.

A visible message represents an EventBridge delivery failure that requires investigation. The operator will review:

- EventBridge error code and error message.
- Exhausted retry condition.
- Retry count.
- EventBridge rule ARN.
- Target ARN.
- Original event payload.
- Lambda resource-based permissions.
- Lambda throttling, availability, and configuration.

EventBridge adds delivery-failure metadata to DLQ messages to support this investigation.

## Recovery procedure

The initial recovery process will be manual:

1. Identify the failed event and review its delivery metadata.
2. Determine whether the cause is permissions, throttling, configuration, availability, or an invalid target.
3. Correct the target or permission failure.
4. Preserve the original message while the investigation remains open.
5. Resubmit the original event to the custom EventBridge bus.
6. Confirm that the event reaches Lambda and is stored in the evidence bucket.
7. Delete the DLQ message only after successful processing is verified.
8. Record the failure, root cause, recovery action, and verification evidence.

Automatic replay will not be enabled during the MVP. Manual replay reduces the risk of repeatedly submitting malformed, unsupported, or malicious events.

## Security considerations

- DLQ messages may contain sensitive cloud-security evidence.
- Queue access will follow least privilege.
- Encryption at rest will remain enabled.
- All queue access must use TLS.
- Message retention will be limited to 14 days.
- Message deletion will require deliberate operator action.
- Events must not contain credentials or unnecessary personal data.
- CloudTrail will provide an audit trail for supported SQS management API activity.
- CloudWatch will alert when failed deliveries require investigation.
- The queue policy will restrict EventBridge access to the intended rule ARN.

## Cost considerations

Amazon SQS charges are request-based. The DLQ should receive messages only when EventBridge exhausts its configured delivery attempts.

Expected development usage is minimal and must remain within the project's USD 15 monthly AWS budget.

A sustained increase in DLQ messages may indicate a broken target or retry loop and must be investigated promptly.

## Deployment dependency

The DLQ will be implemented when the following resources are available:

- The normalization Lambda function.
- The EventBridge rule that selects supported findings.
- The EventBridge target that invokes Lambda.

Waiting for the rule allows the SQS policy to use its exact ARN instead of granting broad access to every EventBridge rule in the AWS account.

## Planned Terraform relationship

The future Terraform configuration will connect the resources as follows:

```text
Custom EventBridge bus
        |
        v
EventBridge detection rule
        |
        v
Lambda target
        |
        +---- delivery failure ----> SQS dead-letter queue
```

The EventBridge target will reference:

```hcl
dead_letter_config {
  arn = aws_sqs_queue.eventbridge_dlq.arn
}

retry_policy {
  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 6
}
```

The queue policy will use the EventBridge rule ARN as its `aws:SourceArn` condition.

## Validation plan

The completed implementation will be tested by temporarily configuring a controlled target failure.

The test will verify that:

1. EventBridge matches the synthetic finding.
2. Delivery to the target fails in a controlled manner.
3. EventBridge applies the configured retry policy.
4. The event appears in the DLQ.
5. The message contains useful delivery-failure metadata.
6. The failure is corrected.
7. The original event is replayed successfully.
8. The event reaches Lambda and the evidence bucket.
9. The test message is removed only after successful processing is confirmed.

The failure simulation must not disable protections on production or unrelated resources.

## Acceptance criteria

The implementation will be complete when:

- [ ] A standard encrypted SQS queue exists in `us-east-1`.
- [ ] The queue retains messages for 14 days.
- [ ] Terraform protects the queue from accidental destruction.
- [ ] The queue policy permits only the intended EventBridge rule to call `sqs:SendMessage`.
- [ ] Insecure transport is denied.
- [ ] The EventBridge target references the DLQ ARN.
- [ ] The retry policy is configured explicitly.
- [ ] A CloudWatch alarm detects visible DLQ messages.
- [ ] A controlled target failure produces a DLQ message.
- [ ] The DLQ message contains useful failure metadata.
- [ ] A corrected event can be replayed successfully.
- [ ] Terraform reports no unexpected changes after deployment.

## References

- https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-dlq.html
- https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html
- https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html
- https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-server-side-encryption.html
