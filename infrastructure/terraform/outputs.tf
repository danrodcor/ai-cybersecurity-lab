output "evidence_bucket_name" {
  description = "Name of the S3 bucket used to store security evidence."
  value       = aws_s3_bucket.evidence.id
}

output "evidence_bucket_arn" {
  description = "ARN of the S3 bucket used to store security evidence."
  value       = aws_s3_bucket.evidence.arn
}

output "security_event_bus_name" {
  description = "Name of the EventBridge bus used to receive security findings."
  value       = aws_cloudwatch_event_bus.security_findings.name
}

output "security_event_bus_arn" {
  description = "ARN of the EventBridge bus used to receive security findings."
  value       = aws_cloudwatch_event_bus.security_findings.arn
}

output "incident_table_name" {
  description = "Name of the DynamoDB table used to store incident metadata."
  value       = aws_dynamodb_table.incidents.name
}

output "incident_table_arn" {
  description = "ARN of the DynamoDB table used to store incident metadata."
  value       = aws_dynamodb_table.incidents.arn
}

output "finding_normalizer_function_name" {
  description = "Name of the Lambda function that normalizes security findings."
  value       = aws_lambda_function.finding_normalizer.function_name
}

output "finding_normalizer_function_arn" {
  description = "ARN of the Lambda function that normalizes security findings."
  value       = aws_lambda_function.finding_normalizer.arn
}

output "finding_normalizer_log_group_name" {
  description = "Name of the CloudWatch log group for the finding normalizer."
  value       = aws_cloudwatch_log_group.finding_normalizer.name
}

output "finding_normalizer_rule_name" {
  description = "Name of the EventBridge rule that invokes the finding normalizer."
  value       = aws_cloudwatch_event_rule.finding_normalizer.name
}
