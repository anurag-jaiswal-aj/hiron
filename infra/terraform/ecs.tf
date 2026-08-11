# AWS ECS & ECR Infrastructure

# 1. ECR Repository
resource "aws_ecr_repository" "hiron_api" {
  name                 = "hiron-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

resource "aws_ecr_lifecycle_policy" "hiron_api_lifecycle" {
  repository = aws_ecr_repository.hiron_api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# 2. CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs_api" {
  name              = "/ecs/hiron-production-api"
  retention_in_days = 30
}

# 3. Secrets Manager (Metadata Only)
resource "aws_secretsmanager_secret" "api_secrets" {
  name        = "production/hiron/api-secrets"
  description = "Production API Secrets (DATABASE_URL, APP_SECRET_KEY, REDIS_URL, OPENAI_API_KEY)"
}
# NOTE: No aws_secretsmanager_secret_version is defined to keep secrets out of Terraform state.

# 4. ECS Task Definition
resource "aws_ecs_task_definition" "hiron_api" {
  family                   = "hiron-api-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_api_cpu
  memory                   = var.ecs_api_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  # Explicit empty volumes map to Fargate ephemeral storage (20GB default)
  volume {
    name = "tmp-volume"
  }

  volume {
    name = "storage-volume"
  }

  container_definitions = jsonencode([
    {
      name      = "hiron-api-container"
      image     = "${aws_ecr_repository.hiron_api.repository_url}:latest"
      cpu       = var.ecs_api_cpu
      memory    = var.ecs_api_memory
      essential = true

      # Hardening
      privileged             = false
      readonlyRootFilesystem = true

      mountPoints = [
        {
          sourceVolume  = "tmp-volume"
          containerPath = "/tmp"
          readOnly      = false
        },
        {
          sourceVolume  = "storage-volume"
          containerPath = "/app/storage"
          readOnly      = false
        }
      ]

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.api_secrets.arn}:DATABASE_URL::"
        },
        {
          name      = "APP_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.api_secrets.arn}:APP_SECRET_KEY::"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.api_secrets.arn}:REDIS_URL::"
        },
        {
          name      = "OPENAI_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.api_secrets.arn}:OPENAI_API_KEY::"
        }
      ]
    }
  ])
}

# 5. ECS Service
resource "aws_ecs_service" "hiron_api" {
  name                               = "hiron-api-service"
  cluster                            = aws_ecs_cluster.production.id
  task_definition                    = aws_ecs_task_definition.hiron_api.arn
  desired_count                      = var.ecs_min_capacity
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "hiron-api-container"
    container_port   = 8000
  }

  # Ensure the ALB listener is ready before service deployment
  depends_on = [
    aws_lb_listener.https,
    aws_lb_listener.http_redirect
  ]
}
