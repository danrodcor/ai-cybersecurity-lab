resource "aws_cloudwatch_event_bus" "security_findings" {
  name = "${local.name_prefix}-security-findings"

  tags = {
    Purpose            = "SecurityFindingIngestion"
    DataClassification = "Internal"
  }
}
