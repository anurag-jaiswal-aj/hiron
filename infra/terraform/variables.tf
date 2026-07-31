# Terraform Input Variables for Hiron Production Deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
  default     = "hiron.ai"
}

variable "vpc_cidr" {
  description = "CIDR block for production VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "Database RDS instance type"
  type        = string
  default     = "db.r6g.large"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 100
}

variable "ecs_api_cpu" {
  description = "CPU units for ECS API tasks (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_api_memory" {
  description = "Memory (MB) for ECS API tasks"
  type        = number
  default     = 2048
}

variable "ecs_min_capacity" {
  description = "Minimum number of tasks in ECS auto scaling"
  type        = number
  default     = 2
}

variable "ecs_max_capacity" {
  description = "Maximum number of tasks in ECS auto scaling"
  type        = number
  default     = 10
}
