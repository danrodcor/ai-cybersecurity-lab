locals {
  approval_functions = {
    request = {
      name        = "approval-request"
      description = "Creates and persists pending human approval requests."
      handler     = "approval_workflow.handlers.create_request_handler"
      purpose     = "CreateApprovalRequests"
      s3_prefix   = "approval-requests"
    }

    decision = {
      name        = "approval-decision"
      description = "Validates and persists human approval decisions."
      handler     = "approval_workflow.handlers.record_decision_handler"
      purpose     = "RecordApprovalDecisions"
      s3_prefix   = "approval-decisions"
    }
  }
}

data "archive_file" "approval_workflow" {
  type        = "zip"
  source_dir  = "${path.root}/../../src"
  output_path = "${path.module}/build/approval-workflow.zip"

  excludes = [
    "__pycache__",
    "__pycache__/*",
    "ai_investigator",
    "ai_investigator/*",
    "finding_normalizer",
    "finding_normalizer/*",
    "reviewer_interface",
    "reviewer_interface/*",
    "approval_workflow/__pycache__",
    "approval_workflow/__pycache__/*",

  ]
}

data "aws_iam_policy_document" "approval_assume_role" {
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

resource "aws_iam_role" "approval_workflow" {
  for_each = local.approval_functions

  name = "${local.name_prefix}-${each.value.name}"

  assume_role_policy = (
    data.aws_iam_policy_document.approval_assume_role.json
  )

  tags = {
    Purpose = each.value.purpose
  }
}

resource "aws_cloudwatch_log_group" "approval_workflow" {
  for_each = local.approval_functions

  name = (
    "/aws/lambda/${local.name_prefix}-${each.value.name}"
  )

  retention_in_days = 14

  tags = {
    Purpose            = "${each.value.purpose}Logs"
    DataClassification = "Sensitive"
  }
}

data "aws_iam_policy_document" "approval_workflow" {
  for_each = local.approval_functions

  statement {
    sid    = "WriteFunctionLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${aws_cloudwatch_log_group.approval_workflow[each.key].arn}:*",
    ]
  }

  statement {
    sid    = "WriteApprovalEvidence"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      "${aws_s3_bucket.evidence.arn}/${each.value.s3_prefix}/*",
    ]
  }

  statement {
    sid    = "UpdateIncidentApprovalState"
    effect = "Allow"

    actions = [
      "dynamodb:UpdateItem",
    ]

    resources = [
      aws_dynamodb_table.incidents.arn,
    ]
  }
}

resource "aws_iam_role_policy" "approval_workflow" {
  for_each = local.approval_functions

  name = "${local.name_prefix}-${each.value.name}"
  role = aws_iam_role.approval_workflow[each.key].id

  policy = (
    data.aws_iam_policy_document.approval_workflow[each.key].json
  )
}

resource "aws_lambda_function" "approval_workflow" {
  for_each = local.approval_functions

  function_name = (
    "${local.name_prefix}-${each.value.name}"
  )
  description = each.value.description

  filename         = data.archive_file.approval_workflow.output_path
  source_code_hash = data.archive_file.approval_workflow.output_base64sha256

  role = aws_iam_role.approval_workflow[each.key].arn

  handler = each.value.handler
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
    Purpose = each.value.purpose
  }

  depends_on = [
    aws_cloudwatch_log_group.approval_workflow,
    aws_iam_role_policy.approval_workflow,
  ]
}

output "approval_request_function_name" {
  description = "Name of the approval-request Lambda function."
  value = (
    aws_lambda_function.approval_workflow["request"].function_name
  )
}

output "approval_decision_function_name" {
  description = "Name of the approval-decision Lambda function."
  value = (
    aws_lambda_function.approval_workflow["decision"].function_name
  )
}
