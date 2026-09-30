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

  dynamic "additional_configuration" {
    for_each = each.value == "RUNTIME_MONITORING" ? toset([
      "EC2_AGENT_MANAGEMENT",
      "ECS_FARGATE_AGENT_MANAGEMENT",
      "EKS_ADDON_MANAGEMENT",
    ]) : toset([])

    content {
      name   = additional_configuration.value
      status = "DISABLED"
    }
  }
}

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name           = "${local.name_prefix}-native-guardduty-findings"
  description    = "Routes native GuardDuty findings to the finding normalizer."
  event_bus_name = "default"

  event_pattern = jsonencode({
    source = [
      "aws.guardduty",
    ]
    detail-type = [
      "GuardDuty Finding",
    ]
  })

  tags = {
    Purpose = "RouteNativeGuardDutyFindings"
  }
}

resource "aws_lambda_permission" "allow_guardduty_eventbridge" {
  statement_id  = "AllowNativeGuardDutyEventBridgeInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finding_normalizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.guardduty_findings.arn
}

resource "aws_cloudwatch_event_target" "guardduty_findings" {
  rule           = aws_cloudwatch_event_rule.guardduty_findings.name
  event_bus_name = aws_cloudwatch_event_rule.guardduty_findings.event_bus_name
  target_id      = "NativeGuardDutyFindingNormalizer"
  arn            = aws_lambda_function.finding_normalizer.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 2
  }

  depends_on = [
    aws_lambda_permission.allow_guardduty_eventbridge,
  ]
}