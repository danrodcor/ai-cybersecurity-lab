variable "aws_region" {
  description = "AWS region used for the Terraform state backend."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to identify the laboratory resources."
  type        = string
  default     = "ai-cybersecurity-lab"
}

variable "owner" {
  description = "Owner recorded in the resource tags."
  type        = string
  default     = "Daniel Rodriguez"
}
