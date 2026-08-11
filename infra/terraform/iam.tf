# AWS IAM Configuration for ECS

# 1. ECS Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "hiron-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# 2. Attach AWS Managed Task Execution Policy (ECR & CloudWatch)
resource "aws_iam_role_policy_attachment" "ecs_execution_managed_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 3. Narrowly Scoped Inline Policy for Secrets Manager
resource "aws_iam_role_policy" "ecs_execution_secrets_policy" {
  name = "hiron-ecs-secrets-policy"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.api_secrets.arn
        ]
      }
    ]
  })
}
