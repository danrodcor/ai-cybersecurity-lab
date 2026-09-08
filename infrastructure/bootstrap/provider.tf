provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "bootstrap"
      Owner       = var.owner
      ManagedBy   = "Terraform"
    }
  }
}
