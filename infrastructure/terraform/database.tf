# Database Infrastructure: RDS PostgreSQL and ElastiCache Redis

# Random password for the RDS instance
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# RDS PostgreSQL Database
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.project_name}-db"

  # Database configuration
  engine            = "postgres"
  engine_version    = "15.7"
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  max_allocated_storage = 1000
  storage_type      = "gp3"
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  # Database details
  db_name  = "checkguard"
  username = "checkguard"
  manage_master_user_password = false
  password = random_password.db_password.result
  port     = "5432"

  # Network configuration
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.database.id]

  # Backup configuration
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  delete_automated_backups = false

  # Enhanced monitoring
  monitoring_interval    = "60"
  monitoring_role_name   = "${var.project_name}-rds-monitoring-role"
  create_monitoring_role = true

  # Performance Insights
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  performance_insights_retention_period = 7

  # Parameter and option groups
  family = "postgres15"
  major_engine_version = "15"

  parameters = [
    {
      name  = "log_statement"
      value = "all"
    },
    {
      name  = "log_min_duration_statement"
      value = "1000"
    },
    {
      name  = "log_connections"
      value = "1"
    },
    {
      name  = "log_disconnections"
      value = "1"
    },
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    }
  ]

  # CloudWatch logs
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true
  cloudwatch_log_group_retention_in_days = 7

  # Security
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier_prefix = "${var.project_name}-final-snapshot"

  # IAM database authentication
  iam_database_authentication_enabled = false

  # Multi-AZ deployment for high availability
  multi_az = true

  # Apply changes immediately in non-production environments
  apply_immediately = var.environment != "production" ? true : false

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Copy tags to snapshots
  copy_tags_to_snapshot = true

  tags = {
    Name        = "${var.project_name}-database"
    Environment = var.environment
    Service     = "database"
  }
}

# ElastiCache Redis for caching and sessions
module "elasticache" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  replication_group_id = "${var.project_name}-redis"

  # Engine configuration
  engine         = "redis"
  engine_version = "7.0"
  node_type      = "cache.t3.micro"

  # Replication configuration
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled          = true

  # Security
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  auth_token                = random_password.redis_auth_token.result

  # Maintenance
  maintenance_window = "sun:05:00-sun:06:00"
  apply_immediately  = var.environment != "production" ? true : false

  # Auto upgrades
  auto_minor_version_upgrade = true

  # Network configuration
  subnet_ids = module.vpc.private_subnets

  # Security group configuration
  vpc_id = module.vpc.vpc_id
  security_group_rules = {
    ingress_ecs = {
      description                  = "Redis from ECS"
      type                        = "ingress"
      from_port                   = 6379
      to_port                     = 6379
      protocol                    = "tcp"
      referenced_security_group_id = aws_security_group.ecs.id
    }
  }

  # Parameter group
  create_parameter_group = true
  parameter_group_family = "redis7"
  parameters = [
    {
      name  = "maxmemory-policy"
      value = "allkeys-lru"
    },
    {
      name  = "timeout"
      value = "300"
    },
    {
      name  = "tcp-keepalive"
      value = "60"
    }
  ]

  # Backup configuration
  snapshot_retention_limit = 7
  snapshot_window         = "02:00-03:00"

  # Log delivery configuration
  log_delivery_configuration = [
    {
      destination      = aws_cloudwatch_log_group.elasticache.name
      destination_type = "cloudwatch-logs"
      log_format      = "json"
      log_type        = "slow-log"
    }
  ]

  tags = {
    Name        = "${var.project_name}-redis"
    Environment = var.environment
    Service     = "cache"
  }
}

# Random password for Redis auth token
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false  # Redis auth tokens don't support special characters
}

# KMS key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for ${var.project_name} RDS encryption"
  deletion_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-rds-kms-key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project_name}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# KMS key for ElastiCache encryption
resource "aws_kms_key" "elasticache" {
  description             = "KMS key for ${var.project_name} ElastiCache encryption"
  deletion_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-elasticache-kms-key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "elasticache" {
  name          = "alias/${var.project_name}-elasticache"
  target_key_id = aws_kms_key.elasticache.key_id
}

# CloudWatch Log Group for ElastiCache
resource "aws_cloudwatch_log_group" "elasticache" {
  name              = "/aws/elasticache/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-elasticache-logs"
    Environment = var.environment
  }
}

# S3 bucket for file uploads (replacing LocalStack)
resource "aws_s3_bucket" "uploads" {
  bucket        = "${var.project_name}-uploads-${random_string.bucket_suffix.result}"
  force_destroy = var.environment != "production" ? true : false

  tags = {
    Name        = "${var.project_name}-uploads"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Random string for S3 bucket suffix
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Outputs consolidated in outputs.tf