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