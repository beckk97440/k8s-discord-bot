# GLOBALS

variable "project_name" {
  description = "Name of the project (prefix for resources)"
  type        = string
  default     = "k8s-discord-bot"
}

variable "aws_region" {
  description = "Region AWS"
  type        = string
  default     = "eu-west-3"  # Paris
}


# NETWORK

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block of public subnet"
  type        = string
  default     = "10.0.1.0/24"
}


# EC2 INSTANCE

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small" 
}


# TAILSCALE

variable "healthcheck_url" {
  description = "URL of my laptop tailscale funnel"
  type        = string
  # No default, in terraform.tfvars
}

variable "tailscale_auth_key" {
  description = "Auth Key Tailscale"
  type        = string
  sensitive   = true  # Hidden in logs
  # No default, in terraform.tfvars
}