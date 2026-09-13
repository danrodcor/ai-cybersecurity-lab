resource "aws_dynamodb_table" "incidents" {
  name         = "${local.name_prefix}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "finding_id"

  attribute {
    name = "finding_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Purpose            = "IncidentMetadata"
    DataClassification = "Sensitive"
  }

  lifecycle {
    prevent_destroy = true
  }
}
