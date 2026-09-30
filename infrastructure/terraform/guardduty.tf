resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  tags = {
    Purpose = "ThreatDetection"
  }

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  guardduty_disabled_features = toset([
    "S3_DATA_EVENTS",
    "EKS_AUDIT_LOGS",
    "EBS_MALWARE_PROTECTION",
    "RDS_LOGIN_EVENTS",
    "LAMBDA_NETWORK_LOGS",
    "RUNTIME_MONITORING",
  ])
}

resource "aws_guardduty_detector_feature" "disabled" {
  for_each = local.guardduty_disabled_features

  detector_id = aws_guardduty_detector.main.id
  name        = each.value
  status      = "DISABLED"
}