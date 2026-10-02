data "aws_iam_policy_document" "approval_state_machine_assume_role" {
  statement {
    sid     = "AllowStepFunctionsService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "approval_state_machine" {
  name = "${local.name_prefix}-approval-workflow"

  assume_role_policy = (
    data.aws_iam_policy_document.approval_state_machine_assume_role.json
  )

  tags = {
    Purpose = "OrchestrateHumanApproval"
  }
}

resource "aws_cloudwatch_log_group" "approval_state_machine" {
  name = (
    "/aws/vendedlogs/states/${local.name_prefix}-approval-workflow"
  )

  retention_in_days = 14

  tags = {
    Purpose            = "ApprovalWorkflowLogs"
    DataClassification = "Sensitive"
  }
}

data "aws_iam_policy_document" "approval_state_machine" {
  statement {
    sid    = "InvokeApprovalRequest"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.approval_workflow["request"].arn,
      "${aws_lambda_function.approval_workflow["request"].arn}:*",
    ]
  }

  statement {
    sid    = "ReadApprovalStatus"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
    ]

    resources = [
      aws_dynamodb_table.incidents.arn,
    ]
  }

  statement {
    sid    = "DeliverExecutionLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "approval_state_machine" {
  name = "${local.name_prefix}-approval-workflow"
  role = aws_iam_role.approval_state_machine.id

  policy = (
    data.aws_iam_policy_document.approval_state_machine.json
  )
}

resource "aws_sfn_state_machine" "approval_workflow" {
  name     = "${local.name_prefix}-approval-workflow"
  role_arn = aws_iam_role.approval_state_machine.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment        = "Wait for a validated human approval decision."
    StartAt        = "CreateApprovalRequest"
    TimeoutSeconds = 90000

    States = {
      CreateApprovalRequest = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"

        Parameters = {
          FunctionName = (
            aws_lambda_function.approval_workflow["request"].arn
          )
          "Payload.$" = "$"
        }

        ResultSelector = {
          "approval_request.$" = (
            "$.Payload.approval_request"
          )
          "persistence.$" = "$.Payload.persistence"
        }

        ResultPath = "$.request"

        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
            ]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]

        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.workflow_error"
            Next        = "WorkflowFailed"
          }
        ]

        Next = "WaitForDecision"
      }

      WaitForDecision = {
        Type    = "Wait"
        Seconds = 30
        Next    = "ReadApprovalStatus"
      }

      ReadApprovalStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:getItem"

        Parameters = {
          TableName = aws_dynamodb_table.incidents.name
          Key = {
            finding_id = {
              "S.$" = "$.finding_id"
            }
          }
          ConsistentRead = true
        }

        ResultPath = "$.approval_record"

        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]

        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.workflow_error"
            Next        = "WorkflowFailed"
          }
        ]

        Next = "EvaluateApprovalStatus"
      }

      EvaluateApprovalStatus = {
        Type = "Choice"

        Choices = [
          {
            Variable     = "$.approval_record.Item.approval_status.S"
            StringEquals = "APPROVED"
            Next         = "ApprovalApproved"
          },
          {
            Variable     = "$.approval_record.Item.approval_status.S"
            StringEquals = "REJECTED"
            Next         = "ApprovalRejected"
          },
          {
            Variable = (
              "$.approval_record.Item.approval_expires_at.S"
            )
            TimestampLessThanPath = "$$.State.EnteredTime"
            Next                  = "ApprovalExpired"
          },
          {
            Variable     = "$.approval_record.Item.approval_status.S"
            StringEquals = "PENDING"
            Next         = "WaitForDecision"
          }
        ]

        Default = "InvalidApprovalState"
      }

      ApprovalApproved = {
        Type = "Pass"
        Result = {
          workflow_status = "APPROVED"
          response_mode   = "DRY_RUN"
        }
        ResultPath = "$.workflow"
        End        = true
      }

      ApprovalRejected = {
        Type = "Pass"
        Result = {
          workflow_status = "REJECTED"
          response_mode   = "DRY_RUN"
        }
        ResultPath = "$.workflow"
        End        = true
      }

      ApprovalExpired = {
        Type = "Pass"
        Result = {
          workflow_status = "EXPIRED"
          response_mode   = "DRY_RUN"
        }
        ResultPath = "$.workflow"
        End        = true
      }

      InvalidApprovalState = {
        Type  = "Fail"
        Error = "InvalidApprovalState"
        Cause = "The stored approval state is unsupported."
      }

      WorkflowFailed = {
        Type  = "Fail"
        Error = "ApprovalWorkflowFailed"
        Cause = "The approval workflow could not continue."
      }
    }
  })

  logging_configuration {
    log_destination = (
      "${aws_cloudwatch_log_group.approval_state_machine.arn}:*"
    )
    include_execution_data = true
    level                  = "ALL"
  }

  tags = {
    Purpose = "OrchestrateHumanApproval"
  }

  depends_on = [
    aws_iam_role_policy.approval_state_machine,
  ]
}

output "approval_workflow_state_machine_arn" {
  description = "ARN of the human-approval state machine."
  value       = aws_sfn_state_machine.approval_workflow.arn
}
