output "evidence_bucket_name" {
  description = "Name of the S3 bucket used to store security evidence."
  value       = aws_s3_bucket.evidence.id
}

output "evidence_bucket_arn" {
  description = "ARN of the S3 bucket used to store security evidence."
  value       = aws_s3_bucket.evidence.arn
}
