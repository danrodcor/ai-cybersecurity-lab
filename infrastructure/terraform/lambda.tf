data "archive_file" "finding_normalizer" {
  type        = "zip"
  source_dir  = "${path.root}/../../src/finding_normalizer"
  output_path = "${path.module}/build/finding-normalizer.zip"

  excludes = [
    "__pycache__",
    "__pycache__/*",
  ]
}

data "aws_iam_policy_document" "finding_normalizer_assume_role" {
  statement {
    sid     = "AllowLambdaService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "finding_normalizer" {
  name               = "${local.name_prefix}-finding-normalizer"
  assume_role_policy = data.aws_iam_policy_document.finding_normalizer_assume_role.json

  tags = {
    Purpose = "NormalizeSecurityFindings"
  }
}

resource "aws_cloudwatch_log_group" "finding_normalizer" {
  name              = "/aws/lambda/${local.name_prefix}-finding-normalizer"
  retention_in_days = 14

  tags = {
    Purpose            = "FindingNormalizerLogs"
    DataClassification = "Sensitive"
  }
}

data "aws_iam_policy_document" "finding_normalizer_logs" {
  statement {
    sid = "WriteFunctionLogs"

    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${aws_cloudwatch_log_group.finding_normalizer.arn}:*",
    ]
  }

  statement {
    sid    = "WriteNormalizedEvidence"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      "${aws_s3_bucket.evidence.arn}/normalized-findings/*",
    ]
  }

  statement {
    sid    = "WriteIncidentMetadata"
    effect = "Allow"

    actions = [
      "dynamodb:PutItem",
    ]

    resources = [
      aws_dynamodb_table.incidents.arn,
    ]
  }
}

resource "aws_iam_role_policy" "finding_normalizer_logs" {
  name   = "${local.name_prefix}-finding-normalizer-logs"
  role   = aws_iam_role.finding_normalizer.id
  policy = data.aws_iam_policy_document.finding_normalizer_logs.json
}

resource "aws_lambda_function" "finding_normalizer" {
  function_name = "${local.name_prefix}-finding-normalizer"
  description   = "Normalizes synthetic GuardDuty findings received from EventBridge."

  filename         = data.archive_file.finding_normalizer.output_path
  source_code_hash = data.archive_file.finding_normalizer.output_base64sha256

  role    = aws_iam_role.finding_normalizer.arn
  handler = "handler.lambda_handler"
  runtime = "python3.13"

  architectures = ["x86_64"]
  memory_size   = 128
  timeout       = 10

  environment {
    variables = {
      EVIDENCE_BUCKET_NAME = aws_s3_bucket.evidence.id
      INCIDENT_TABLE_NAME  = aws_dynamodb_table.incidents.name
    }
  }

  tags = {
    Purpose = "NormalizeSecurityFindings"
  }

  depends_on = [
    aws_cloudwatch_log_group.finding_normalizer,
    aws_iam_role_policy.finding_normalizer_logs,
  ]
}

resource "aws_cloudwatch_event_rule" "finding_normalizer" {
  name           = "${local.name_prefix}-normalize-findings"
  description    = "Routes synthetic GuardDuty findings to the finding normalizer."
  event_bus_name = aws_cloudwatch_event_bus.security_findings.name

  event_pattern = jsonencode({
    source = [
      "com.danrodcor.securitylab.guardduty",
    ]
    detail-type = [
      "Synthetic GuardDuty Finding",
    ]
  })

  tags = {
    Purpose = "RouteSecurityFindings"
  }
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finding_normalizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.finding_normalizer.arn
}

resource "aws_cloudwatch_event_target" "finding_normalizer" {
  rule           = aws_cloudwatch_event_rule.finding_normalizer.name
  event_bus_name = aws_cloudwatch_event_bus.security_findings.name
  target_id      = "FindingNormalizerLambda"
  arn            = aws_lambda_function.finding_normalizer.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 2
  }

  depends_on = [
    aws_lambda_permission.allow_eventbridge,
  ]
}
