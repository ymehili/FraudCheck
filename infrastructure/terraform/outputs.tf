# Terraform Outputs - Infrastructure Resources

# Networking Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnets
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "Application Load Balancer ARN"
  value       = aws_lb.main.arn
}

output "alb_url" {
  description = "Application Load Balancer URL"
  value       = "http://${aws_lb.main.dns_name}"
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = module.ecs.cluster_arn
}

output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = module.ecs.cluster_id
}

# ECR Outputs
output "ecr_backend_repository_url" {
  description = "ECR backend repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR frontend repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecr_backend_repository_arn" {
  description = "ECR backend repository ARN"
  value       = aws_ecr_repository.backend.arn
}

output "ecr_frontend_repository_arn" {
  description = "ECR frontend repository ARN"
  value       = aws_ecr_repository.frontend.arn
}

# Database Outputs
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_username" {
  description = "RDS username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = module.rds.db_instance_arn
}

# Redis Outputs
output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache.replication_group_primary_endpoint_address
  sensitive   = true
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint"
  value       = module.elasticache.replication_group_reader_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

output "redis_replication_group_id" {
  description = "Redis replication group ID"
  value       = module.elasticache.replication_group_id
}

output "redis_replication_group_arn" {
  description = "Redis replication group ARN"
  value       = module.elasticache.replication_group_arn
}

# S3 Outputs
output "s3_uploads_bucket_name" {
  description = "S3 uploads bucket name"
  value       = aws_s3_bucket.uploads.bucket
}

output "s3_uploads_bucket_arn" {
  description = "S3 uploads bucket ARN"
  value       = aws_s3_bucket.uploads.arn
}

output "s3_alb_logs_bucket_name" {
  description = "S3 ALB logs bucket name"
  value       = aws_s3_bucket.alb_logs.bucket
}

output "s3_alb_logs_bucket_arn" {
  description = "S3 ALB logs bucket ARN"
  value       = aws_s3_bucket.alb_logs.arn
}

# Security Group Outputs
output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = aws_security_group.ecs.id
}

output "database_security_group_id" {
  description = "Database security group ID"
  value       = aws_security_group.database.id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

# IAM Role Outputs
output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

output "github_actions_role_arn" {
  description = "GitHub Actions role ARN"
  value       = aws_iam_role.github_actions.arn
}

# Secrets Manager Outputs
output "database_secret_arn" {
  description = "Database secret ARN"
  value       = aws_secretsmanager_secret.database.arn
}

output "redis_secret_arn" {
  description = "Redis secret ARN"
  value       = aws_secretsmanager_secret.redis.arn
}

output "clerk_secret_arn" {
  description = "Clerk secret ARN"
  value       = aws_secretsmanager_secret.clerk.arn
}

output "clerk_publishable_secret_arn" {
  description = "Clerk publishable secret ARN"
  value       = aws_secretsmanager_secret.clerk_publishable.arn
}

output "gemini_secret_arn" {
  description = "Gemini API secret ARN"
  value       = aws_secretsmanager_secret.gemini.arn
}

output "app_secret_arn" {
  description = "Application secret ARN"
  value       = aws_secretsmanager_secret.app_secret.arn
}

# KMS Key Outputs
output "secrets_kms_key_arn" {
  description = "Secrets Manager KMS key ARN"
  value       = aws_kms_key.secrets.arn
}

output "rds_kms_key_arn" {
  description = "RDS KMS key ARN"
  value       = aws_kms_key.rds.arn
}

output "elasticache_kms_key_arn" {
  description = "ElastiCache KMS key ARN"
  value       = aws_kms_key.elasticache.arn
}

# Target Group Outputs
output "backend_target_group_arn" {
  description = "Backend target group ARN"
  value       = aws_lb_target_group.backend.arn
}

output "frontend_target_group_arn" {
  description = "Frontend target group ARN"
  value       = aws_lb_target_group.frontend.arn
}

# CloudWatch Log Group Outputs
output "ecs_log_group_name" {
  description = "ECS CloudWatch log group name"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "elasticache_log_group_name" {
  description = "ElastiCache CloudWatch log group name"
  value       = aws_cloudwatch_log_group.elasticache.name
}

# Application URLs
output "application_url" {
  description = "Application URL (ALB endpoint)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "api_url" {
  description = "API URL (ALB endpoint with /api path)"
  value       = "http://${aws_lb.main.dns_name}/api"
}

output "api_docs_url" {
  description = "API documentation URL"
  value       = "http://${aws_lb.main.dns_name}/docs"
}

# Environment Information
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Deployment Information
output "deployment_info" {
  description = "Deployment information summary"
  value = {
    project_name    = var.project_name
    environment     = var.environment
    aws_region      = var.aws_region
    aws_account_id  = data.aws_caller_identity.current.account_id
    application_url = "http://${aws_lb.main.dns_name}"
    api_url         = "http://${aws_lb.main.dns_name}/api"
    api_docs_url    = "http://${aws_lb.main.dns_name}/docs"
    cluster_name    = module.ecs.cluster_name
    vpc_id          = module.vpc.vpc_id
  }
}