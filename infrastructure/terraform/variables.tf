variable "aws_region" {
  description = "AWS region used to deploy the laboratory resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to identify the project and its AWS resources."
  type        = string
  default     = "ai-cybersecurity-lab"
}

variable "environment" {
  description = "Deployment environment for the laboratory."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, or prod."
  }
}

variable "owner" {
  description = "Owner responsible for the laboratory resources."
  type        = string
  default     = "danrodcor"
}