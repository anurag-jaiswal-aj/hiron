# Terraform Remote S3 Backend with DynamoDB State Locking
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "hiron-terraform-state-prod"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "hiron-terraform-locks"
    encrypt        = true
  }
}
