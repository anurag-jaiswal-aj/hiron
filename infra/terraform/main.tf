# Main Terraform Production AWS Infrastructure Definition

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Hiron"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 1. VPC & Network Topography
resource "aws_vpc" "production" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "hiron-production-vpc"
  }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.production.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "hiron-prod-public-subnet-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.production.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = {
    Name = "hiron-prod-public-subnet-b"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.production.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "hiron-prod-private-subnet-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.production.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "hiron-prod-private-subnet-b"
  }
}

# 2. Security Groups
resource "aws_security_group" "alb" {
  name        = "hiron-alb-sg"
  description = "Allow TLS/HTTP inbound traffic to Application Load Balancer"
  vpc_id      = aws_vpc.production.id

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP redirect to HTTPS"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    ="-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name        = "hiron-ecs-sg"
  description = "Allow inbound traffic from ALB to ECS Fargate tasks"
  vpc_id      = aws_vpc.production.id

  ingress {
    description     = "Traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 3. Amazon ECS Fargate Cluster
resource "aws_ecs_cluster" "production" {
  name = "hiron-production-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# 4. S3 Bucket for Resume & Artifact Storage
resource "aws_s3_bucket" "resumes" {
  bucket = "hiron-production-resumes"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "resumes_crypto" {
  bucket = aws_s3_bucket.resumes.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "resumes_block" {
  bucket                  = aws_s3_bucket.resumes.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
