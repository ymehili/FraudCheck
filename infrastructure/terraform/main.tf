# Terraform AWS ECS Infrastructure for CheckGuard AI
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.93.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "CheckGuard AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "CheckGuard Team"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "checkguard"
}

# Data sources for existing infrastructure
data "aws_availability_zones" "available" {
  state = "available"
}

# ECS Cluster and Services
module "ecs" {
  source = "terraform-aws-modules/ecs/aws"

  cluster_name = "${var.project_name}-cluster"

  cluster_configuration = {
    execute_command_configuration = {
      logging = "OVERRIDE"
      log_configuration = {
        cloud_watch_log_group_name = "/aws/ecs/${var.project_name}"
      }
    }
  }

  # Cluster capacity providers - Fargate for serverless containers
  default_capacity_provider_strategy = {
    FARGATE = {
      weight = 70
      base   = 1
    }
    FARGATE_SPOT = {
      weight = 30
    }
  }

  services = {
    # Backend API Service
    backend = {
      cpu    = 1024
      memory = 2048

      # Use predefined IAM roles with correct permissions
      task_role_arn      = aws_iam_role.ecs_task.arn
      execution_role_arn = aws_iam_role.ecs_task_execution.arn

      # Container definitions
      container_definitions = {
        backend = {
          cpu       = 1024
          memory    = 2048
          essential = true
          image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/checkguard-backend:latest"
          
          portMappings = [
            {
              name          = "backend"
              containerPort = 8000
              hostPort      = 8000
              protocol      = "tcp"
            }
          ]

          # Environment variables (will be overridden by Secrets Manager)
          environment = [
            {
              name  = "NODE_ENV"
              value = "production"
            },
            {
              name  = "API_V1_STR"
              value = "/api/v1"
            },
            {
              name  = "PROJECT_NAME"
              value = "CheckGuard AI"
            }
          ]

          # Secrets from AWS Secrets Manager
          secrets = [
            {
              name      = "DATABASE_URL"
              valueFrom = "${aws_secretsmanager_secret.database.arn}:url::"
            },
            {
              name      = "CLERK_SECRET_KEY"
              valueFrom = aws_secretsmanager_secret.clerk.arn
            },
            {
              name      = "GEMINI_API_KEY"
              valueFrom = aws_secretsmanager_secret.gemini.arn
            },
            {
              name      = "SECRET_KEY"
              valueFrom = aws_secretsmanager_secret.app_secret.arn
            }
          ]

          # Health check
          healthCheck = {
            command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
            interval    = 30
            timeout     = 5
            retries     = 3
            startPeriod = 60
          }

          # Security settings
          readonlyRootFilesystem = false
          user                   = "1000"

          # Logging configuration
          enable_cloudwatch_logging              = true
          cloudwatch_log_group_use_name_prefix   = true
          cloudwatch_log_group_retention_in_days = 7

          # Resource requirements
          memoryReservation = 1024
        }
      }

      load_balancer = {
        service = {
          target_group_arn = aws_lb_target_group.backend.arn
          container_name   = "backend"
          container_port   = 8000
        }
      }

      subnet_ids = module.vpc.private_subnets
      security_group_ingress_rules = {
        alb_8000 = {
          description                  = "Backend API port"
          from_port                    = 8000
          to_port                      = 8000
          ip_protocol                  = "tcp"
          referenced_security_group_id = aws_security_group.alb.id
        }
      }
      security_group_egress_rules = {
        all = {
          ip_protocol = "-1"
          cidr_ipv4   = "0.0.0.0/0"
        }
      }

      # Auto-scaling configuration
      autoscaling_min_capacity = 2
      autoscaling_max_capacity = 10
      autoscaling_policies = {
        cpu = {
          target_tracking_scaling_policy_configuration = {
            predefined_metric_specification = {
              predefined_metric_type = "ECSServiceAverageCPUUtilization"
            }
            target_value = 70.0
          }
        }
        memory = {
          target_tracking_scaling_policy_configuration = {
            predefined_metric_specification = {
              predefined_metric_type = "ECSServiceAverageMemoryUtilization"
            }
            target_value = 80.0
          }
        }
      }
    }

    # Frontend Service
    frontend = {
      cpu    = 512
      memory = 1024

      # Use predefined IAM roles with correct permissions
      task_role_arn      = aws_iam_role.ecs_task.arn
      execution_role_arn = aws_iam_role.ecs_task_execution.arn

      container_definitions = {
        frontend = {
          cpu       = 512
          memory    = 1024
          essential = true
          image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/checkguard-frontend:latest"
          
          portMappings = [
            {
              name          = "frontend"
              containerPort = 3000
              hostPort      = 3000
              protocol      = "tcp"
            }
          ]

          environment = [
            {
              name  = "NODE_ENV"
              value = "production"
            },
            {
              name  = "NEXT_PUBLIC_API_URL"
              value = "https://${aws_lb.main.dns_name}"
            },
            {
              name  = "NEXT_PUBLIC_API_BASE_URL"
              value = "https://${aws_lb.main.dns_name}"
            }
          ]

          secrets = [
            {
              name      = "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
              valueFrom = aws_secretsmanager_secret.clerk_publishable.arn
            }
          ]

          healthCheck = {
            command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1"]
            interval    = 30
            timeout     = 5
            retries     = 3
            startPeriod = 60
          }

          readonlyRootFilesystem = false
          user                   = "1001"

          enable_cloudwatch_logging              = true
          cloudwatch_log_group_use_name_prefix   = true
          cloudwatch_log_group_retention_in_days = 7

          memoryReservation = 512
        }
      }

      load_balancer = {
        service = {
          target_group_arn = aws_lb_target_group.frontend.arn
          container_name   = "frontend"
          container_port   = 3000
        }
      }

      subnet_ids = module.vpc.private_subnets
      security_group_ingress_rules = {
        alb_3000 = {
          description                  = "Frontend port"
          from_port                    = 3000
          to_port                      = 3000
          ip_protocol                  = "tcp"
          referenced_security_group_id = aws_security_group.alb.id
        }
      }
      security_group_egress_rules = {
        all = {
          ip_protocol = "-1"
          cidr_ipv4   = "0.0.0.0/0"
        }
      }

      autoscaling_min_capacity = 1
      autoscaling_max_capacity = 5
      autoscaling_policies = {
        cpu = {
          target_tracking_scaling_policy_configuration = {
            predefined_metric_specification = {
              predefined_metric_type = "ECSServiceAverageCPUUtilization"
            }
            target_value = 70.0
          }
        }
      }
    }

    # Celery Worker Service
    celery-worker = {
      cpu    = 1024
      memory = 2048
      
      # No load balancer for worker service
      create_load_balancer = false

      # Use predefined IAM roles with correct permissions
      task_role_arn      = aws_iam_role.ecs_task.arn
      execution_role_arn = aws_iam_role.ecs_task_execution.arn

      container_definitions = {
        worker = {
          cpu       = 1024
          memory    = 2048
          essential = true
          image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/checkguard-backend:latest"
          command   = ["python", "celery_worker.py"]
          
          environment = [
            {
              name  = "NODE_ENV"
              value = "production"
            }
          ]

          secrets = [
            {
              name      = "DATABASE_URL"
              valueFrom = "${aws_secretsmanager_secret.database.arn}:url::"
            },
            {
              name      = "CELERY_BROKER_URL"
              valueFrom = aws_secretsmanager_secret.redis.arn
            },
            {
              name      = "CELERY_RESULT_BACKEND"
              valueFrom = aws_secretsmanager_secret.redis.arn
            },
            {
              name      = "GEMINI_API_KEY"
              valueFrom = aws_secretsmanager_secret.gemini.arn
            }
          ]

          healthCheck = {
            command     = ["CMD-SHELL", "celery -A app.tasks.celery_app inspect ping || exit 1"]
            interval    = 30
            timeout     = 10
            retries     = 3
            startPeriod = 60
          }

          readonlyRootFilesystem = false
          user                   = "1000"

          enable_cloudwatch_logging              = true
          cloudwatch_log_group_use_name_prefix   = true
          cloudwatch_log_group_retention_in_days = 7

          memoryReservation = 1024
        }
      }

      subnet_ids = module.vpc.private_subnets
      security_group_egress_rules = {
        all = {
          ip_protocol = "-1"
          cidr_ipv4   = "0.0.0.0/0"
        }
      }

      autoscaling_min_capacity = 1
      autoscaling_max_capacity = 5
      autoscaling_policies = {
        cpu = {
          target_tracking_scaling_policy_configuration = {
            predefined_metric_specification = {
              predefined_metric_type = "ECSServiceAverageCPUUtilization"
            }
            target_value = 70.0
          }
        }
      }
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# CloudWatch Log Groups for ECS
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/aws/ecs/${var.project_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}