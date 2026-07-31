# Terraform Output Values for Production Deployment

output "vpc_id" {
  description = "Production VPC ID"
  value       = aws_vpc.production.id
}

output "ecs_cluster_name" {
  description = "ECS Fargate Cluster Name"
  value       = aws_ecs_cluster.production.name
}

output "s3_resumes_bucket_name" {
  description = "Encrypted S3 resume storage bucket name"
  value       = aws_s3_bucket.resumes.id
}
