# Security Configuration: IAM Roles, Policies, and Secrets Manager

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-task-execution-role"
    Environment = var.environment
  }
}

# Attach the default ECS task execution policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for ECS task execution (Secrets Manager access)
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project_name}-ecs-task-execution-secrets-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database.arn,
          aws_secretsmanager_secret.redis.arn,
          aws_secretsmanager_secret.clerk.arn,
          aws_secretsmanager_secret.clerk_publishable.arn,
          aws_secretsmanager_secret.gemini.arn,
          aws_secretsmanager_secret.app_secret.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          aws_kms_key.secrets.arn
        ]
      }
    ]
  })
}

# ECS Task Role (for the application containers)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-task-role"
    Environment = var.environment
  }
}

# ECS Task Policy (S3, Secrets Manager, CloudWatch)
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.project_name}-ecs-task-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.database.arn,
          aws_secretsmanager_secret.redis.arn,
          aws_secretsmanager_secret.gemini.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [
          aws_kms_key.secrets.arn,
          aws_kms_key.rds.arn,
          aws_kms_key.elasticache.arn
        ]
      }
    ]
  })
}

# GitHub Actions Role for CI/CD
resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-github-actions-role"
    Environment = var.environment
  }
}

# GitHub Actions Policy
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "${var.project_name}-github-actions-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [
          aws_ecr_repository.backend.arn,
          aws_ecr_repository.frontend.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:ListTasks",
          "ecs:DescribeTasks",
          "ecs:RunTask"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn,
          "arn:aws:iam::233442448767:role/backend-*",
          "arn:aws:iam::233442448767:role/frontend-*",
          "arn:aws:iam::233442448767:role/celery-worker-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# GitHub OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]

  tags = {
    Name        = "${var.project_name}-github-oidc-provider"
    Environment = var.environment
  }
}

# KMS Key for Secrets Manager
resource "aws_kms_key" "secrets" {
  description             = "KMS key for ${var.project_name} Secrets Manager"
  deletion_window_in_days = 7

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow ECS to decrypt secrets"
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_task_execution.arn,
            aws_iam_role.ecs_task.arn
          ]
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-secrets-kms-key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# Secrets Manager - Database credentials
resource "aws_secretsmanager_secret" "database" {
  name                    = "${var.project_name}/database"
  description             = "Database credentials for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-database-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username = module.rds.db_instance_username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = module.rds.db_instance_endpoint
    port     = module.rds.db_instance_port
    dbname   = module.rds.db_instance_name
    url      = "postgresql+asyncpg://${module.rds.db_instance_username}:${random_password.db_password.result}@${module.rds.db_instance_endpoint}/${module.rds.db_instance_name}"
  })
}

# Secrets Manager - Redis credentials
resource "aws_secretsmanager_secret" "redis" {
  name                    = "${var.project_name}/redis"
  description             = "Redis credentials for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-redis-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({
    auth_token      = random_password.redis_auth_token.result
    primary_endpoint = module.elasticache.replication_group_primary_endpoint_address
    reader_endpoint  = module.elasticache.replication_group_reader_endpoint_address
    port            = 6379
    url             = "redis://:${random_password.redis_auth_token.result}@${module.elasticache.replication_group_primary_endpoint_address}:6379/0"
    broker_url      = "redis://:${random_password.redis_auth_token.result}@${module.elasticache.replication_group_primary_endpoint_address}:6379/0"
    result_backend  = "redis://:${random_password.redis_auth_token.result}@${module.elasticache.replication_group_primary_endpoint_address}:6379/1"
  })
}

# Secrets Manager - Clerk Authentication
resource "aws_secretsmanager_secret" "clerk" {
  name                    = "${var.project_name}/clerk"
  description             = "Clerk authentication secret key for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-clerk-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "clerk" {
  secret_id     = aws_secretsmanager_secret.clerk.id
  secret_string = var.clerk_secret_key
}

# Secrets Manager - Clerk Publishable Key
resource "aws_secretsmanager_secret" "clerk_publishable" {
  name                    = "${var.project_name}/clerk-publishable"
  description             = "Clerk publishable key for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-clerk-publishable-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "clerk_publishable" {
  secret_id     = aws_secretsmanager_secret.clerk_publishable.id
  secret_string = var.clerk_publishable_key
}

# Secrets Manager - Gemini API Key
resource "aws_secretsmanager_secret" "gemini" {
  name                    = "${var.project_name}/gemini"
  description             = "Gemini API key for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-gemini-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "gemini" {
  secret_id     = aws_secretsmanager_secret.gemini.id
  secret_string = var.gemini_api_key
}

# Secrets Manager - Application Secret Key
resource "aws_secretsmanager_secret" "app_secret" {
  name                    = "${var.project_name}/app-secret"
  description             = "Application secret key for ${var.project_name}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-app-secret"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "app_secret" {
  secret_id = aws_secretsmanager_secret.app_secret.id
  secret_string = jsonencode({
    secret_key = random_password.app_secret_key.result
  })
}

# Random secret key for the application
resource "random_password" "app_secret_key" {
  length  = 64
  special = true
}

# Variables for secrets (to be provided externally)
variable "clerk_secret_key" {
  description = "Clerk secret key"
  type        = string
  sensitive   = true
}

variable "clerk_publishable_key" {
  description = "Clerk publishable key"
  type        = string
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
}

variable "github_repository" {
  description = "GitHub repository in the format owner/repo"
  type        = string
  default     = "checkguard/checkguard-ai"
}

# Outputs consolidated in outputs.tf